"""Malayalam Unicode Tokenizer.

Provides Unicode-aware tokenization specifically tailored for Malayalam text,
preserving vowel signs (matras), virama (chandrakkala), anusvara, visarga,
and chillu letters while strictly maintaining 1-based sequential token positions.
"""

import re
import unicodedata
from typing import List, Tuple

try:
    from src.text_preprocessor import TextPreprocessor
except ImportError:
    from text_preprocessor import TextPreprocessor


class MalayalamTokenizer:
    """Unicode-aware tokenizer for Malayalam natural language text."""

    def __init__(self) -> None:
        self.preprocessor = TextPreprocessor()

        # Regex matching Malayalam word units (including combining signs and ZWJ/ZWNJ)
        # as well as standard alphanumeric tokens.
        # Malayalam range: \u0D00-\u0D7F, Joiners: \u200C, \u200D
        self._token_pattern = re.compile(
            r"[\u0D00-\u0D7F\u200C\u200D]+|[A-Za-z0-9]+", re.UNICODE
        )

        # Characters to trim from token edges (such as isolated zero-width characters or symbols)
        self._edge_trim_chars = "\u200c\u200d\u00ad\ufeff \t\n\r"

    def tokenize(self, text: str) -> List[str]:
        """Tokenize input text into a list of normalized tokens.

        Preserves all valid Malayalam characters, vowel signs, and chillu letters.
        Applies Unicode NFC normalization and lowercasing for ASCII tokens.

        Args:
            text: Input text (already cleaned of wiki markup or raw string).

        Returns:
            List of normalized string tokens in original sequential order.
        """
        if not text:
            return []

        # Ensure NFC normalization
        normalized = unicodedata.normalize("NFC", text)

        tokens: List[str] = []
        for match in self._token_pattern.finditer(normalized):
            raw_token = match.group(0)
            token = raw_token.strip(self._edge_trim_chars)
            # Case normalization for Latin characters; Malayalam is unaffected
            token = token.lower()

            if token:
                # Ensure the token itself is normalized NFC
                tokens.append(unicodedata.normalize("NFC", token))

        return tokens

    def tokenize_with_positions(self, text: str) -> List[Tuple[str, int]]:
        """Tokenize input text and assign 1-based sequential positions.

        Per the assignment specification:
        Positions start at 1 for the first token in the document.
        Example:
            Document: 'കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ്'
            Yields:
                ('കേരളം', 1),
                ('ഇന്ത്യയുടെ', 2),
                ('മനോഹരമായ', 3),
                ('സംസ്ഥാനമാണ്', 4)

        Args:
            text: Input text.

        Returns:
            List of (token, 1-based position) tuples.
        """
        tokens = self.tokenize(text)
        return [(token, pos) for pos, token in enumerate(tokens, start=1)]
