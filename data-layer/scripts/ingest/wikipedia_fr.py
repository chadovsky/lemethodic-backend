"""
French Wikipedia ingestion — cultural / civilizational chunks.

Source: https://fr.wikipedia.org via the MediaWiki action API.
License: CC-BY-SA (Wikipedia contributors).

Targets ~2,000 article titles drawn from seven culture-bearing top-level
categories. Each article becomes one chunk:
- surface_fr     ← article display title (proper noun / cultural term)
- _examples      ← lead-paragraph extract (first ~2 sentences) as a single
                    chunk_example linked to the title chunk
- topic_codes    ← {culture-fr-europe, culture-fr-anglo} per source category

Topic mapping:
- culture-fr-europe (DELF — European cultural content):
    Catégorie:Culture_française, Catégorie:Littérature_française,
    Catégorie:Cuisine_française, Catégorie:Société_française
- culture-fr-anglo (AP French — Franco-anglophone cultural overlap):
    Catégorie:Histoire_de_France, Catégorie:Personnalités_françaises,
    Catégorie:Géographie_de_la_France

Pipeline shape (idempotent + resumable):
1. download() walks each top-level category (BFS, depth ≤ 1) collecting
   page titles, capped per-category, then bulk-fetches lead extracts +
   disambiguation flags via prop=extracts|pageprops (50 titles per call).
   Both lists and extracts cache to JSON under raw/wikipediafr/ — a re-run
   reuses the cache and issues zero network requests.
2. iter_rows() reads the cache and yields one chunk dict per qualifying
   article: skips disambiguation pages and stubs (lead < 100 chars), dedups
   by title across categories (first category to encounter the title owns
   the topic_code).
3. _upsert_row() is overridden to attach topic_codes via a follow-up
   UPDATE (the base upsert_chunk doesn't carry topic_codes, by design —
   topic_codes is normally written by enrich.py).

Politeness: a fixed 1 request/second floor between API calls + a
descriptive User-Agent identifying the project (Wikipedia API policy).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Iterator, Optional

import click
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from scripts.common import insert_example, normalize_surface, upsert_chunk
from scripts.ingest.base import Ingester


API_URL = "https://fr.wikipedia.org/w/api.php"
USER_AGENT = (
    "LeMethodicIngester/1.0 "
    "(https://lemethodic.com; chadi.bakhay@gmail.com) "
    "python-requests"
)

# Top-level category → topic_code mapping.
# DELF-relevant European cultural content vs. AP-overlapping Franco-anglophone
# content (history, famous people, geography). Order matters for dedup — the
# first category to see a title wins the topic_code assignment.
CATEGORY_TOPICS: list[tuple[str, str]] = [
    ("Catégorie:Histoire_de_France", "culture-fr-anglo"),
    ("Catégorie:Personnalités_françaises", "culture-fr-anglo"),
    ("Catégorie:Géographie_de_la_France", "culture-fr-anglo"),
    ("Catégorie:Culture_française", "culture-fr-europe"),
    ("Catégorie:Littérature_française", "culture-fr-europe"),
    ("Catégorie:Cuisine_française", "culture-fr-europe"),
    ("Catégorie:Société_française", "culture-fr-europe"),
]


class WikipediaFRIngester(Ingester):
    source_name = "WikipediaFR"
    batch_size = 200

    # Per top-level category cap. 7 categories × 350 ≈ 2,450 raw titles
    # before cross-category dedup → comfortably inside the 1,500–3,000
    # target band quoted in the validation expectation.
    pages_per_top_category: int = 350

    # BFS depth into subcategories. 0 = direct page members only;
    # 1 = also walk one level of subcategories. Top-level cultural categories
    # like "Culture française" carry mostly subcategories, so depth 1 is
    # required to reach actual articles.
    subcategory_depth: int = 1

    # Stub filter: drop articles whose lead extract is shorter than this.
    min_lead_chars: int = 100

    # Bulk extracts API accepts up to 50 titles per call when not logged in.
    extract_batch_size: int = 20

    # Politeness floor: 1 request/second.
    request_delay_seconds: float = 1.0

    def __init__(self) -> None:
        super().__init__()
        # source_version = today's ISO date (snapshots the ingest day —
        # Wikipedia is a moving target with no canonical version string).
        self.source_version = _dt.date.today().isoformat()

        self.titles_dir = self.raw_dir / "titles_by_category"
        self.summaries_dir = self.raw_dir / "summaries"
        self.titles_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_path = self.raw_dir / "title_topic_map.json"

        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_request_at: float = 0.0

    # -- Polite GET ------------------------------------------------------

    def _api_get(self, params: dict) -> dict:
        """Throttled JSON GET against the MediaWiki action API."""
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self.request_delay_seconds:
            time.sleep(self.request_delay_seconds - elapsed)
        request_params = dict(params)
        request_params["format"] = "json"
        request_params["formatversion"] = "2"
        try:
            r = self.session.get(API_URL, params=request_params, timeout=30)
            r.raise_for_status()
            return r.json()
        finally:
            self._last_request_at = time.monotonic()

    # -- Category walking ------------------------------------------------

    def _list_pages_in_category(
        self,
        category: str,
        cap: Optional[int] = None,
    ) -> list[str]:
        """Page (cmtype=page) members of `category`, paginated via cmcontinue."""
        out: list[str] = []
        cont: Optional[str] = None
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmtype": "page",
                "cmlimit": "500",
            }
            if cont:
                params["cmcontinue"] = cont
            data = self._api_get(params)
            members = data.get("query", {}).get("categorymembers", []) or []
            for m in members:
                title = m.get("title")
                # Skip non-article namespaces just in case (cmtype=page should
                # only return main-namespace articles, but defensively filter).
                if not title or ":" in title.split(" ", 1)[0]:
                    continue
                out.append(title)
                if cap is not None and len(out) >= cap:
                    return out
            cont = (data.get("continue") or {}).get("cmcontinue")
            if not cont:
                break
        return out

    def _list_subcategories(self, category: str) -> list[str]:
        out: list[str] = []
        cont: Optional[str] = None
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmtype": "subcat",
                "cmlimit": "500",
            }
            if cont:
                params["cmcontinue"] = cont
            data = self._api_get(params)
            members = data.get("query", {}).get("categorymembers", []) or []
            for m in members:
                t = m.get("title")
                if t:
                    out.append(t)
            cont = (data.get("continue") or {}).get("cmcontinue")
            if not cont:
                break
        return out

    def _collect_titles(self, top_category: str) -> list[str]:
        """BFS down to self.subcategory_depth, capped at self.pages_per_top_category."""
        seen_categories: set[str] = set()
        seen_titles: set[str] = set()
        ordered_titles: list[str] = []

        def take(titles: list[str]) -> bool:
            """Append unseen titles; return True once cap is reached."""
            for t in titles:
                if t in seen_titles:
                    continue
                seen_titles.add(t)
                ordered_titles.append(t)
                if len(ordered_titles) >= self.pages_per_top_category:
                    return True
            return False

        # Frontier = (category, depth). Process FIFO so direct members come first.
        frontier: list[tuple[str, int]] = [(top_category, 0)]
        while frontier:
            current, depth = frontier.pop(0)
            if current in seen_categories:
                continue
            seen_categories.add(current)

            self.log.info(f"  walking {current} (depth={depth})")
            page_titles = self._list_pages_in_category(
                current,
                cap=self.pages_per_top_category - len(ordered_titles),
            )
            if take(page_titles):
                break

            if depth < self.subcategory_depth:
                subcats = self._list_subcategories(current)
                for sc in subcats:
                    if sc not in seen_categories:
                        frontier.append((sc, depth + 1))

        return ordered_titles

    # -- Bulk extracts ---------------------------------------------------

    def _fetch_extracts(self, titles: list[str]) -> dict[str, dict]:
        """
        Bulk-fetch lead extracts + disambiguation flags for a batch of titles.

        Returns {requested_title: {"resolved_title", "extract", "is_disambiguation", "missing"}}.
        Uses prop=extracts (intro only, plain text, ~2 sentences) plus
        prop=pageprops (the `disambiguation` page-prop is set on dab pages).
        Honors `redirects=1` so we follow redirects to the canonical article.
        """
        if not titles:
            return {}
        params = {
            "action": "query",
            "prop": "extracts|pageprops",
            "exintro": "1",
            "explaintext": "1",
            "exsentences": "2",
            "ppprop": "disambiguation",
            "redirects": "1",
            "titles": "|".join(titles),
        }
        data = self._api_get(params)
        query = data.get("query", {}) or {}

        # Build a redirect map: {requested_title: resolved_title}.
        redirect_map = {
            r.get("from"): r.get("to")
            for r in query.get("redirects", []) or []
            if r.get("from") and r.get("to")
        }
        # Normalization map (e.g. spaces vs underscores, capitalization).
        normalize_map = {
            n.get("from"): n.get("to")
            for n in query.get("normalized", []) or []
            if n.get("from") and n.get("to")
        }

        # Index returned pages by their final title.
        pages_by_title: dict[str, dict] = {}
        for p in query.get("pages", []) or []:
            t = p.get("title")
            if t:
                pages_by_title[t] = p

        out: dict[str, dict] = {}
        for requested in titles:
            normalized_title = normalize_map.get(requested, requested)
            resolved_title = redirect_map.get(normalized_title, normalized_title)
            page = pages_by_title.get(resolved_title)
            if page is None:
                out[requested] = {
                    "resolved_title": resolved_title,
                    "extract": "",
                    "is_disambiguation": False,
                    "missing": True,
                }
                continue
            pageprops = page.get("pageprops") or {}
            out[requested] = {
                "resolved_title": page.get("title", resolved_title),
                "extract": page.get("extract", "") or "",
                "is_disambiguation": "disambiguation" in pageprops,
                "missing": bool(page.get("missing")),
            }
        return out

    @staticmethod
    def _summary_path_for(summaries_dir: Path, title: str) -> Path:
        slug = hashlib.md5(title.encode("utf-8")).hexdigest()[:16]
        return summaries_dir / f"{slug}.json"

    @staticmethod
    def _category_filename(category: str) -> str:
        # "Catégorie:Culture_française" → "Categorie_Culture_francaise"
        cleaned = re.sub(r"[^\w]+", "_", category, flags=re.UNICODE)
        return cleaned.strip("_") + ".json"

    # -- Required Ingester hooks ----------------------------------------

    def download(self) -> None:
        """Walk categories + bulk-fetch summaries. Caches everything."""
        title_to_topic: dict[str, str] = {}

        for category, topic_code in CATEGORY_TOPICS:
            cache_path = self.titles_dir / self._category_filename(category)
            if cache_path.exists():
                titles = json.loads(cache_path.read_text(encoding="utf-8"))
                self.log.info(
                    f"Cached titles for {category}: {len(titles)} (topic={topic_code})"
                )
            else:
                self.log.info(f"Listing pages for {category} (topic={topic_code})")
                titles = self._collect_titles(category)
                cache_path.write_text(
                    json.dumps(titles, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                self.log.info(f"  Found {len(titles)} pages in {category}")

            for t in titles:
                title_to_topic.setdefault(t, topic_code)

        self.mapping_path.write_text(
            json.dumps(title_to_topic, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.log.info(
            f"Title→topic map: {len(title_to_topic)} unique titles "
            f"({sum(1 for v in title_to_topic.values() if v == 'culture-fr-europe')} europe / "
            f"{sum(1 for v in title_to_topic.values() if v == 'culture-fr-anglo')} anglo)"
        )

        # Fetch summaries in batches; cache one JSON per requested title.
        all_titles = list(title_to_topic.keys())
        to_fetch = [
            t for t in all_titles
            if not self._summary_path_for(self.summaries_dir, t).exists()
        ]
        self.log.info(
            f"Summary cache: {len(all_titles) - len(to_fetch)}/{len(all_titles)} hit; "
            f"fetching {len(to_fetch)} new"
        )

        for i in range(0, len(to_fetch), self.extract_batch_size):
            batch = to_fetch[i:i + self.extract_batch_size]
            try:
                results = self._fetch_extracts(batch)
            except Exception as e:  # noqa: BLE001
                self.log.error(f"Extract batch failed ({batch[0]}…): {e}")
                continue
            for requested_title, result in results.items():
                fp = self._summary_path_for(self.summaries_dir, requested_title)
                fp.write_text(
                    json.dumps({"requested_title": requested_title, **result}, ensure_ascii=False),
                    encoding="utf-8",
                )
            if (i // self.extract_batch_size) % 10 == 0 and i:
                self.log.info(
                    f"  fetched {min(i + self.extract_batch_size, len(to_fetch))}/{len(to_fetch)} summaries"
                )

    def iter_rows(self) -> Iterator[dict]:
        if not self.mapping_path.exists():
            raise RuntimeError(
                f"Title mapping not found at {self.mapping_path} — run download() first."
            )
        title_to_topic: dict[str, str] = json.loads(
            self.mapping_path.read_text(encoding="utf-8")
        )

        # Within iter_rows we also dedupe by normalized surface form so that
        # different requested titles that resolve to the same article (via
        # redirect) don't produce duplicate sources rows in the same run.
        seen_normalized: set[str] = set()

        skipped_missing = 0
        skipped_disambig = 0
        skipped_stub = 0
        skipped_dup = 0
        emitted = 0

        for requested_title, topic_code in title_to_topic.items():
            fp = self._summary_path_for(self.summaries_dir, requested_title)
            if not fp.exists():
                skipped_missing += 1
                continue
            try:
                summary = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                skipped_missing += 1
                continue
            if summary.get("missing"):
                skipped_missing += 1
                continue
            if summary.get("is_disambiguation"):
                skipped_disambig += 1
                continue

            extract = (summary.get("extract") or "").strip()
            if len(extract) < self.min_lead_chars:
                skipped_stub += 1
                continue

            resolved_title = (summary.get("resolved_title") or requested_title).strip()
            if not resolved_title:
                skipped_missing += 1
                continue

            normalized = normalize_surface(resolved_title)
            if not normalized or normalized in seen_normalized:
                skipped_dup += 1
                continue
            seen_normalized.add(normalized)

            emitted += 1
            yield {
                "surface_fr": resolved_title,
                "language": "fr",
                "is_quebec_specific": False,
                # cefr_level intentionally NULL — filled by enrichment later.
                "_topic_codes": [topic_code],
                "_examples": [{"example_fr": extract, "example_en": None}],
            }

        self.log.info(
            f"iter_rows complete: emitted={emitted} "
            f"skipped(missing={skipped_missing}, disambig={skipped_disambig}, "
            f"stub={skipped_stub}, dup={skipped_dup})"
        )

    # -- Override to attach topic_codes ----------------------------------

    def _upsert_row(self, session: Session, row: dict) -> None:
        topic_codes = row.pop("_topic_codes", []) or []
        examples = row.pop("_examples", []) or []
        surface = row.pop("surface_fr", None)
        if not surface or not surface.strip():
            return

        contributed = list(row.keys())
        if topic_codes:
            contributed.append("topic_codes")

        chunk_id = upsert_chunk(
            session=session,
            surface_fr=surface,
            source_name=self.source_name,
            source_version=self.source_version,
            source_license=self.license_info.get("license"),
            contributed_fields=contributed,
            **row,
        )

        if topic_codes:
            # Merge topic_codes into the existing array, deduped, preserving
            # any codes another source already attached. ARRAY_AGG(DISTINCT)
            # is idempotent — a re-run of the same source on the same chunk
            # leaves topic_codes unchanged.
            session.execute(text("""
                UPDATE chunks
                SET topic_codes = (
                    SELECT COALESCE(ARRAY_AGG(DISTINCT t ORDER BY t), ARRAY[]::TEXT[])
                    FROM unnest(
                        COALESCE(chunks.topic_codes, ARRAY[]::TEXT[])
                        || CAST(:new_codes AS TEXT[])
                    ) AS t
                )
                WHERE id = :cid
            """), {"new_codes": topic_codes, "cid": chunk_id})

        for ex in examples:
            insert_example(
                session=session,
                chunk_id=chunk_id,
                example_fr=ex.get("example_fr", ""),
                example_en=ex.get("example_en"),
                cefr_level=ex.get("cefr_level"),
                source_name=self.source_name,
            )


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    WikipediaFRIngester().run()


if __name__ == "__main__":
    main()
