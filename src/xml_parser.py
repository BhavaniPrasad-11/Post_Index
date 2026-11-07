"""Malayalam Wikipedia XML Dump Streaming Parser.

Uses streaming XML parsing (xml.etree.ElementTree.iterparse) on bz2 compressed
or uncompressed Wikimedia dumps to iterate over Wikipedia articles one-by-one
without loading the complete XML dump into RAM.

Filters out non-article namespaces (templates, talk, categories) and redirects,
assigning unique sequential numerical DocIDs.
"""

import bz2
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Generator, NamedTuple, Optional

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
try:
    from src.text_preprocessor import TextPreprocessor
except ImportError:
    from text_preprocessor import TextPreprocessor


class WikiArticle(NamedTuple):
    """Structured representation of an extracted Wikipedia article."""

    doc_id: int
    wiki_id: int
    title: str
    url: str
    cleaned_text: str
    raw_length: int


class WikipediaXMLParser:
    """Streams and parses Wikipedia articles from an XML or XML.BZ2 dump."""

    def __init__(self, dump_path: Path = config.DUMP_PATH) -> None:
        self.dump_path = Path(dump_path)
        self.preprocessor = TextPreprocessor()

    def stream_articles(
        self, max_docs: Optional[int] = None
    ) -> Generator[WikiArticle, None, None]:
        """Stream articles one by one from the XML dump.

        Yields:
            WikiArticle namedtuples with doc_id, wiki_id, title, url, and cleaned_text.
        """
        if not self.dump_path.exists():
            raise FileNotFoundError(f"Wikipedia dump not found at {self.dump_path}")

        # Open file stream: bz2 decompressor stream or standard text stream
        if self.dump_path.suffix == ".bz2":
            file_stream = bz2.BZ2File(self.dump_path, "rb")
        else:
            file_stream = open(self.dump_path, "rb")

        current_doc_id = 0

        try:
            # iterparse generates (event, elem) tuples
            context = ET.iterparse(file_stream, events=("end",))
            _, root = next(context)  # get root element

            for event, elem in context:
                # Local tag without namespace
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

                if tag == "page":
                    # Check namespace: <ns>0</ns> is main article namespace
                    ns_elem = elem.find("./{*}ns")
                    if ns_elem is None:
                        ns_elem = elem.find("ns")
                    ns_val = ns_elem.text.strip() if (ns_elem is not None and ns_elem.text) else ""

                    # Exclude non-article namespaces
                    if ns_val != "0":
                        elem.clear()
                        root.clear()
                        continue

                    # Check for redirect: <redirect title="..." />
                    is_redirect = (
                        elem.find("./{*}redirect") is not None
                        or elem.find("redirect") is not None
                    )
                    if is_redirect:
                        elem.clear()
                        root.clear()
                        continue

                    # Extract title
                    title_elem = elem.find("./{*}title")
                    if title_elem is None:
                        title_elem = elem.find("title")
                    title = title_elem.text.strip() if (title_elem is not None and title_elem.text) else ""

                    # Filter out MediaWiki administrative or internal pages if any slipped in
                    if not title or ":" in title and any(
                        title.startswith(pfx)
                        for pfx in ["വിഭാഗം:", "ഫയൽ:", "പ്രത്യേകം:", "സഹായം:", "വിക്കിപീഡിയ:"]
                    ):
                        elem.clear()
                        root.clear()
                        continue

                    # Extract wiki page id
                    id_elem = elem.find("./{*}id")
                    if id_elem is None:
                        id_elem = elem.find("id")
                    wiki_id = int(id_elem.text.strip()) if (id_elem is not None and id_elem.text and id_elem.text.strip().isdigit()) else 0

                    # Extract wikitext
                    text_elem = elem.find("./{*}revision/{*}text")
                    if text_elem is None:
                        text_elem = elem.find(".//text")
                    raw_text = text_elem.text if (text_elem is not None and text_elem.text) else ""

                    if not raw_text.strip():
                        elem.clear()
                        root.clear()
                        continue

                    # Clean wikitext
                    cleaned_text = self.preprocessor.clean_wikitext(raw_text)

                    if not cleaned_text:
                        elem.clear()
                        root.clear()
                        continue

                    current_doc_id += 1
                    url = f"{config.WIKI_BASE_URL}{urllib_quote(title)}"

                    yield WikiArticle(
                        doc_id=current_doc_id,
                        wiki_id=wiki_id,
                        title=title,
                        url=url,
                        cleaned_text=cleaned_text,
                        raw_length=len(raw_text),
                    )

                    # Clear element and root children to prevent memory accumulation
                    elem.clear()
                    root.clear()

                    if max_docs is not None and current_doc_id >= max_docs:
                        break

        finally:
            file_stream.close()


def urllib_quote(title: str) -> str:
    """Helper to quote title safely for URL generation."""
    import urllib.parse
    return urllib.parse.quote(title.replace(" ", "_"))
