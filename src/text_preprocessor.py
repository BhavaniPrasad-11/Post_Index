"""Malayalam Text Preprocessor.

Performs Unicode NFC normalization, Wikipedia markup removal, HTML/template
stripping, and text sanitization while preserving authentic Malayalam characters,
vowel signs, conjuncts, and chillu letters.
"""

import html
import re
import unicodedata
from typing import Optional


class TextPreprocessor:
    """Preprocesses raw Malayalam text and Wikipedia markup."""

    def __init__(self) -> None:
        # Regex patterns precompiled for performance
        self._comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        self._ref_block_pattern = re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
        self._ref_self_pattern = re.compile(r"<ref[^>]*/>", re.IGNORECASE)
        self._tag_block_pattern = re.compile(
            r"<(gallery|math|code|timeline|score)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
        )
        self._html_tag_pattern = re.compile(r"<[^>]+>")
        self._table_pattern = re.compile(r"\{\|.*?\|\}", re.DOTALL)
        self._category_file_pattern = re.compile(
            r"\[\[(?:Category|വർഗ്ഗം|File|Image|പ്രമാണം):.*?\]\]", re.IGNORECASE
        )
        self._wiki_link_pattern = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
        self._ext_link_pattern = re.compile(r"\[https?://\S+\s+([^\]]+)\]")
        self._url_pattern = re.compile(r"https?://\S+")
        self._header_pattern = re.compile(r"={2,}\s*([^=]+?)\s*={2,}")
        self._multi_whitespace_pattern = re.compile(r"\s+")

    def clean_wikitext(self, raw_text: Optional[str]) -> str:
        """Strip Wikipedia markup, templates, HTML, and irrelevant metadata.

        Args:
            raw_text: Raw wikitext string extracted from Wikipedia XML.

        Returns:
            Cleaned natural language text in Malayalam.
        """
        if not raw_text:
            return ""

        # Unescape HTML entities (&amp;, &quot;, &#123;, etc.)
        text = html.unescape(raw_text)

        # Remove XML/HTML comments
        text = self._comment_pattern.sub(" ", text)

        # Remove reference tags and citation contents
        text = self._ref_block_pattern.sub(" ", text)
        text = self._ref_self_pattern.sub(" ", text)

        # Remove special mediawiki tags (math, gallery, etc.)
        text = self._tag_block_pattern.sub(" ", text)

        # Remove tables {| ... |}
        text = self._table_pattern.sub(" ", text)

        # Remove templates {{...}}, handling shallow nesting up to 6 levels
        for _ in range(6):
            new_text = re.sub(r"\{\{[^{}]*\}\}", " ", text, flags=re.DOTALL)
            if new_text == text:
                break
            text = new_text

        # Remove categories, file links, and embedded images
        text = self._category_file_pattern.sub(" ", text)

        # Extract anchor/link text from internal wikilinks [[Target|Anchor]] -> Anchor
        text = self._wiki_link_pattern.sub(r"\1", text)

        # Extract link text from external links [url label] -> label
        text = self._ext_link_pattern.sub(r"\1", text)

        # Remove raw URLs
        text = self._url_pattern.sub(" ", text)

        # Replace section headings == Title == with Title
        text = self._header_pattern.sub(r"\1", text)

        # Remove remaining generic HTML tags
        text = self._html_tag_pattern.sub(" ", text)

        # Normalize Unicode to NFC
        text = self.normalize_unicode(text)

        # Collapse whitespace
        text = self._multi_whitespace_pattern.sub(" ", text).strip()
        return text

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Apply Unicode NFC normalization.

        NFC (Canonical Decomposition, followed by Canonical Composition) ensures
        consistent binary representations for Malayalam compound characters,
        matras (vowel signs), and chillu sequences.

        Args:
            text: Input string.

        Returns:
            NFC normalized string.
        """
        if not text:
            return ""
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def normalize_case(text: str) -> str:
        """Apply case normalization where applicable (e.g. for Latin tokens).

        Malayalam script has no upper/lower case distinction, but mixed
        content (acronyms, names) benefits from case folding.

        Args:
            text: Input string.

        Returns:
            Case-folded string.
        """
        if not text:
            return ""
        return text.lower()
