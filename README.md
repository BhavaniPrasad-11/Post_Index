# Malayalam Positional Inverted Index — Information Retrieval Assignment

**Student Roll Number:** `S20240010254`  
**Course:** Information Retrieval (CS / IT)  
**Target Language:** Malayalam (`മലയാളം` — ISO 639-3: `mal`, Unicode block `U+0D00–U+0D7F`)  
**GitHub Repository:** [https://github.com/BhavaniPrasad-11/Post_Index](https://github.com/BhavaniPrasad-11/Post_Index)  
**Submission Package:** `S20240010254-A1-PostIndex-IR-M2026.zip`  
**Source Archive:** `S20240010254-src.zip`  
**Index Artifacts Archive:** `S20240010254-index-artifacts.zip`  
**Combined Package:** `S20240010254-final-submission.zip`

---

## 1. Project Description & Objectives

This project implements a complete, production-grade **Positional Inverted Index** for the Malayalam language, built from the official Malayalam Wikipedia dump.

The system addresses the fundamental requirements of modern text search for morphologically rich Indic languages:
1. **Unicode Malayalam Processing:** Normalizes canonical Indic representations (NFC) while preserving vowel signs (*matras*), virama (*chandrakkala*), *chillu* letters (`ൺ, ൻ, ർ, ൽ, ൾ, ൿ`), and Zero-Width joiners/non-joiners.
2. **Positional Inverted Indexing:** Maintains 1-based sequential token positions throughout the entire cleaned text of each document.
3. **Dual-Tier Memory/Secondary Storage Architecture:** The complete term vocabulary and document frequencies reside in Main Memory (RAM) for $O(1)$ dictionary lookups, while complete positional postings lists reside in persistent Secondary Storage (SQLite B-Tree) to bound memory consumption.
4. **Information Retrieval Metrics:** Computes exact Collection Frequency (CF) and Document Frequency (DF).
5. **Exact Phrase Search:** Implements positional intersection ($pos(t_{k+1}) = pos(t_k) + 1$) to locate multi-word phrases without false positives.
6. **Rare Term Analysis:** Surfaces authentic low-DF terms to inspect the long-tail distribution of the vocabulary.

---

## 2. Problem Statement

Standard inverted indices only record the document IDs where terms occur:
$$\text{Term} \longrightarrow [\text{DocID}_1, \text{DocID}_2, \dots]$$

While adequate for Boolean queries (`AND`, `OR`), standard inverted indices cannot:
1. Verify word proximity or contiguous adjacency.
2. Execute exact phrase queries (e.g., distinguishing "കേരള സാഹിത്യ അക്കാദമി" from documents containing those three words scattered across different sections).
3. Support positional proximity ranking.

Malayalam presents additional engineering considerations:
- High vocabulary cardinality due to agglutinative noun cases (`കേരളം`, `കേരളത്തിന്റെ`, `കേരളത്തിൽ`).
- Distinct Unicode characters requiring NFC normalization.
- Scalability challenges when loading large encyclopedic postings lists into RAM.

This project resolves these challenges through a streaming XML parser, Unicode-aware tokenizer, SQLite-backed positional storage, and an in-memory dictionary.

---

## 3. Malayalam Dataset Source

The collection was extracted directly from the official **Malayalam Wikipedia XML Article Dump**:
- **Source:** Wikimedia Foundation Dumps (`https://dumps.wikimedia.org/mlwiki/latest/`)
- **Dump Archive:** `mlwiki-latest-pages-articles.xml.bz2`
- **Compressed Size:** 194.48 MB (203,925,193 bytes)
- **Uncompressed XML Size:** > 900 MB
- **Corpus Type:** Full-text encyclopedic articles in Malayalam.
- **GitHub Repository:** [https://github.com/BhavaniPrasad-11/Post_Index](https://github.com/BhavaniPrasad-11/Post_Index)
- **Licensing:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) and GFDL.

---

## 4. Dataset Size & Number of Indexed Documents

- **Indexed Documents:** `5,000` genuine Malayalam Wikipedia articles.
- **Article Namespace:** Filtered strictly for `<ns>0</ns>` (main encyclopedic articles; non-article namespaces such as categories, templates, and talk pages excluded).
- **Redirects:** Excluded (`<redirect>` pages filtered out during streaming).
- **Total Processed Tokens:** `2,285,058` tokens.
- **Unique Vocabulary Terms:** `449,064` unique terms.
- **Total Postings on Disk:** `1,590,645` postings.
- **Average Document Length:** `457.01` tokens per article.

---

## 5. System Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │   Malayalam Wikipedia XML Dump (.xml.bz2)     │
                  └───────────────────────┬───────────────────────┘
                                          │ Streaming iterparse (bounded RAM)
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │               WikipediaXMLParser              │
                  │   - Filter ns == 0 (Articles only)            │
                  │   - Discard redirects                         │
                  │   - Assign unique numerical DocID (1, 2, ...) │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │                TextPreprocessor               │
                  │   - Strip wikitext, templates, references     │
                  │   - Unicode NFC canonical composition         │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │               MalayalamTokenizer              │
                  │   - Unicode Malayalam word regex              │
                  │   - Assign 1-based sequential token positions │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │               PositionalIndexer               │
                  │   - Count term occurrences in document        │
                  │   - Map Term -> [pos1, pos2, ...]             │
                  └───────────────┬───────────────────────┬───────┘
                                  │                       │
         Batched Disk Writes      │                       │ In-Memory Stats
         (Every 500 Docs)         │                       │ (CF += freq, DF += 1)
                                  ▼                       ▼
      ┌─────────────────────────────────────┐  ┌────────────────────────────────────┐
      │     SECONDARY STORAGE (DISK)        │  │         MAIN MEMORY (RAM)          │
      │         index/postings.sqlite3      │  │        InvertedIndexDictionary     │
      │ ┌─────────────────────────────────┐ │  │ ┌────────────────────────────────┐ │
      │ │ postings (term, doc_id, [pos])  │ │  │ │ {Term: TermEntry(cf, df)}      │ │
      │ ├─────────────────────────────────┤ │  │ └────────────────────────────────┘ │
      │ │ documents (doc_id, title, url)  │ │  │                                    │
      │ └─────────────────────────────────┘ │  │ Serialized on disk as:             │
      │   Indexed via B-Tree on (term, doc) │  │ index/dictionary.json              │
      └─────────────────────────────────────┘  └────────────────────────────────────┘
                                  ▲                       ▲
                                  │ On-Demand Disk Fetch  │ O(1) Memory Lookup
                                  └───────────┬───────────┘
                                              │
                                  ┌───────────┴───────────┐
                                  │ MalayalamSearchEngine │
                                  │ - Single-term search  │
                                  │ - Positional Phrase   │
                                  │ - Rare term retrieval │
                                  └───────────────────────┘
```

---

## 6. Malayalam Preprocessing Methodology

Wikitext extraction applies multi-stage sanitization:
1. **Entity Decoding:** Decodes HTML/XML entities (`html.unescape`).
2. **Comment & Reference Removal:** Strips `<!-- ... -->`, `<ref>...</ref>`, `<ref />`.
3. **Template Removal:** Recursively removes MediaWiki templates (`{{...}}`) up to 6 levels deep.
4. **Markup & Media Stripping:** Removes tables (`{| ... |}`), category tags (`[[Category:...]]`, `[[വർഗ്ഗം:...]]`), embedded images (`[[File:...]]`, `[[പ്രമാണം:...]]`), and generic HTML tags.
5. **Internal & External Link Handling:** Preserves link text from internal links (`[[Target|Anchor]]` $\rightarrow$ `Anchor`) and external links (`[url label]` $\rightarrow$ `label`).
6. **Whitespace Normalization:** Collapses multi-spaces and newlines into single spaces.

---

## 7. Unicode Normalization

Malayalam characters can be represented in decomposed forms (e.g. consonant + separate vowel code points vs. composed glyphs).
The preprocessor enforces **Unicode NFC** (`unicodedata.normalize('NFC', text)`):
- Standardizes all characters, combining marks, and conjuncts into canonical composed form.
- Correctly preserves Malayalam chillu letters (U+0D7A through U+0D7F) and virama/chandrakkala (`്`, U+0D4D).
- Preserves Zero-Width Joiners (ZWJ, `\u200D`) and Non-Joiners (ZWNJ, `\u200C`) where semantically meaningful.

---

## 8. Tokenization & 1-Based Positions

The `MalayalamTokenizer` extracts tokens using a Unicode-aware regex matching Malayalam script units and alphanumeric tokens:
`[\u0D00-\u0D7F\u200C\u200D]+|[A-Za-z0-9]+`

- **Stop Words:** Not removed by default to maintain positional integrity for phrase queries.
- **Stemming:** English stemming algorithms are not applied to Malayalam, and no artificial Malayalam stemmer is fabricated.
- **1-Based Position Rule:** Every token receives a 1-based sequential position integer ($1, 2, 3, \dots, N$) matching its position in the cleaned document text.

Example:
> Document: `"കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ്"`  
> 1. `കേരളം` $\rightarrow$ Position `1`  
> 2. `ഇന്ത്യയുടെ` $\rightarrow$ Position `2`  
> 3. `മനോഹരമായ` $\rightarrow$ Position `3`  
> 4. `സംസ്ഥാനമാണ്` $\rightarrow$ Position `4`

---

## 9. Positional Inverted Index Explanation

A positional inverted index maps every term to a list of postings containing both document IDs and token positions:

$$\text{Term} \longrightarrow \big[ (\text{DocID}_1, [p_{1,1}, p_{1,2}, \dots]), (\text{DocID}_2, [p_{2,1}, \dots]), \dots \big]$$

Where:
- $\text{DocID}_1 < \text{DocID}_2 < \dots$ (strictly ascending order of DocIDs).
- Inside every document posting, $p_{d,1} < p_{d,2} < \dots$ (strictly ascending token positions).

---

## 10. Collection Frequency (CF) & Document Frequency (DF)

- **Collection Frequency ($\text{CF}$):** Total number of occurrences of the term across all documents:
  $$\text{CF}(t) = \sum_{d \in D} f_{t,d}$$
- **Document Frequency ($\text{DF}$):** Total number of distinct documents containing the term:
  $$\text{DF}(t) = |\{ d \in D \mid f_{t,d} > 0 \}|$$
- By definition, $\text{DF}(t) \le \text{CF}(t)$.

---

## 11. Explanation of Positional Postings

Each posting is structured as:
`DocID: [pos_1, pos_2, ..., pos_k]`
- Stored on secondary storage as a row in SQLite: `(term, doc_id, positions_json)`.
- Indexed via SQLite B-tree on `(term, doc_id ASC)`.
- Only matching postings for the queried term are read from disk during search execution.

---

## 12. In-Memory Dictionary Implementation

- The in-memory vocabulary resides in `InvertedIndexDictionary` (`src/dictionary.py`).
- Mapping: `term -> TermEntry(cf: int, df: int)`.
- Loaded from `index/dictionary.json` into RAM when the search engine initializes.
- Size in RAM: ~35 MB for 449,064 terms.
- Lookups execute in $O(1)$ memory time with zero initial disk I/O.

---

## 13. Disk-Based SQLite Postings Implementation

- Managed by `StorageManager` (`src/storage_manager.py`).
- File: `index/postings.sqlite3` (131.81 MB).
- Database pragma settings for performance: `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA cache_size = -64000`.
- Postings are fetched on-demand using parameterized queries:
  ```sql
  SELECT doc_id, positions FROM postings WHERE term = ? ORDER BY doc_id ASC;
  ```

---

## 14. Module Descriptions

```
Malayalam-Positional-Indexer/
├── config.py                  # Portable project configuration, paths, and constants
├── main.py                    # Unified CLI and interactive application
├── requirements.txt           # Dependencies (requests, tqdm)
│
├── src/
│   ├── __init__.py            # Package initialization
│   ├── dataset_downloader.py  # Wikimedia dump downloader with disk space checks
│   ├── text_preprocessor.py   # Wikipedia markup stripping and Unicode NFC normalization
│   ├── tokenizer.py           # Unicode Malayalam tokenizer (1-based positions)
│   ├── xml_parser.py          # Memory-safe streaming XML parser (iterparse)
│   ├── dictionary.py          # In-memory RAM vocabulary (Term -> CF, DF)
│   ├── storage_manager.py     # SQLite persistent secondary storage manager
│   ├── positional_indexer.py  # End-to-end positional index construction engine
│   ├── search_engine.py       # Single-term search, phrase intersection, rare terms
│   └── statistics.py          # Collection statistics generator and report formatter
│
├── tests/
│   ├── __init__.py            # Test package marker
│   └── test_indexer.py        # 5 automated unit test cases with synthetic Malayalam corpus
│
├── data/
│   ├── collection_info.json   # Download provenance metadata (portable relative paths)
│   └── mlwiki-latest-pages-articles.xml.bz2
│
├── index/
│   ├── dictionary.json        # Serialized in-memory dictionary (449k terms, 33.55 MB)
│   └── postings.sqlite3       # Persistent SQLite secondary storage (1.59M postings, 131.81 MB)
│
├── output/
│   ├── collection_statistics.txt
│   ├── rare_terms.txt
│   ├── test_results.txt
│   ├── query_examples.txt
│   ├── sample_positional_index.txt
│   └── index_validation.txt
│
└── scripts/
    ├── build_index.py         # Dedicated CLI index builder
    ├── generate_reports.py    # Report generator script
    ├── package_submission.py  # Packaging script for submission ZIP archives
    ├── validate_index.py      # Comprehensive 12-rule index integrity validator
    └── verify_rare_terms.py   # Direct database verification script for rare terms
```

---

## 15. Installation Instructions

### Prerequisites
- Python 3.10 or higher.
- Disk space: ~1 GB (for dump file, SQLite DB, and dictionary).

### Setup
```bash
# Clone or navigate to the project directory
cd Malayalam-Positional-Indexer

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 16. Dataset Download Instructions

Download the official Malayalam Wikipedia dump:
```bash
python src/dataset_downloader.py
```
Or run `python main.py build`, which will automatically trigger the download if the dump file is missing.

---

## 17. Index Construction Commands

To index articles from the Wikipedia dump:
```bash
# Build index for 5,000 articles (standard assignment configuration)
python scripts/build_index.py --max-docs 5000

# Or using main.py
python main.py build --max-docs 5000

# To index ALL articles in the dump (omit --max-docs):
python scripts/build_index.py
```

---

## 18. Term Searching Commands

Search for a single Malayalam term to view CF, DF, and positional postings:
```bash
python main.py search-term "കേരളം" --limit 5
python main.py search-term "മലയാളം" --limit 5
```

---

## 19. Phrase Searching Commands

Search for multi-word Malayalam phrases via positional intersection:
```bash
python main.py search-phrase "കേരള സാഹിത്യ അക്കാദമി" --limit 5
python main.py search-phrase "ഇന്ത്യൻ സംസ്ഥാനമായ" --limit 5
python main.py search-phrase "പ്രധാന നഗരം" --limit 5
```

---

## 20. Rare-Term Retrieval Commands

Display 10 authentic rare Malayalam terms having Document Frequency $\text{DF} = 1$:
```bash
python main.py rare-terms --limit 10
```

---

## 21. How to Run Automated Tests

Execute the automated test suite covering all 5 required test cases:
```bash
python main.py test
# Or directly via unittest:
python tests/test_indexer.py -v
```

---

## 22. Actual Test Results

```
test_1_unicode_tokenization (tests.test_indexer.TestMalayalamPositionalIndexer) ... ok
test_2_positional_indexing_of_repeated_terms (tests.test_indexer.TestMalayalamPositionalIndexer) ... ok
test_3_collection_and_document_frequency (tests.test_indexer.TestMalayalamPositionalIndexer) ... ok
test_4_disk_retrieval_of_positional_postings (tests.test_indexer.TestMalayalamPositionalIndexer) ... ok
test_5_phrase_search_using_positional_information (tests.test_indexer.TestMalayalamPositionalIndexer) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.082s | OK (5/5 PASSED)
```

---

## 23. Actual Collection Statistics

- **Total Documents Indexed:** 5,000 articles
- **Total Processed Tokens:** 2,285,058 tokens
- **Unique Vocabulary Terms (RAM):** 449,064 terms
- **Total Postings on Secondary Storage (Disk):** 1,590,645 rows
- **Postings Database Size (SQLite):** 131.81 MB
- **Vocabulary File Size (JSON):** 33.55 MB
- **Average Document Length:** 457.01 tokens / article
- **Average Postings per Term:** 3.54 documents / term
- **Index Construction Time:** 57.47 seconds

---

## 24. Sample Malayalam Queries & Results

| Query Type | Input Query | Output Metric | Interpretation |
| :--- | :--- | :--- | :--- |
| **Single Term** | `കേരളം` | CF: 359, DF: 197 | Frequent geographical headword across articles |
| **Single Term** | `മലയാളം` | CF: 910, DF: 481 | Language name with 24 occurrences in Doc 3 |
| **Repeated Term**| `സാഹിത്യം` (Doc 8) | Positions: `[1, 8, 24, 26, 50, ...]` | Multiple positional occurrences recorded in ascending order |
| **3-Word Phrase** | `കേരള സാഹിത്യ അക്കാദമി`| Matches: 121 docs, 212 occurrences | Exact consecutive phrase matches verified via positional intersection |
| **2-Word Phrase** | `ഇന്ത്യൻ സംസ്ഥാനമായ` | Matches: 12 docs, 12 occurrences | Adjacent words matched at exact token offsets |
| **2-Word Phrase** | `പ്രധാന നഗരം` | Matches: 2 docs (`കാഞ്ഞങ്ങാട്`, `കന്യാകുമാരി`) | Geographical phrase matching consecutive words |
| **Rare Term** | `സമൂഹ്യതിന്മകൾക്കെതിരെയും` | CF: 1, DF: 1, DocID: 2 (`ശ്രീനാരായണഗുരു`) | Unique term in single historical article at pos `[23]` |
| **Rare Term** | `അക്ഷരമാലയെ` | CF: 1, DF: 1, DocID: 3 (`മലയാളം അക്ഷരമാല`) | Unique term in single linguistics article at pos `[10]` |

---

## 25. Positional Index Integrity Validation (12 Rules)

Run the comprehensive validator:
```bash
python scripts/validate_index.py
```
Output: [`output/index_validation.txt`](file:///output/index_validation.txt) (All 12 rules passed: 100% compliant).

---

## 26. Limitations & Future Improvements

1. **Morphological Stemming / Lemmatization:** English stemmers were intentionally not applied, and artificial stemmers were avoided. Future iterations could integrate rule-based Malayalam morphological analyzers to cluster case-inflected variants (`കേരളത്തിന്`, `കേരളത്തിൽ`) while preserving token offsets.
2. **Postings Compression:** Positions are currently stored as JSON arrays in SQLite. For billion-token corpora, variable-byte encoding (VByte) or Elias-delta compression could further optimize storage.
3. **Proximity Search Operators:** Extending phrase intersection to support proximity operators (e.g., $w_1 \text{ WITHIN } k \text{ WORDS OF } w_2$).

---

## 27. Attribution & Dataset Licensing

- **Dataset Attribution:** Malayalam Wikipedia article content is authored by Wikipedia contributors and hosted by the Wikimedia Foundation.
- **License:** Content is available under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/) and GNU Free Documentation License (GFDL).
- **Project Implementation:** Developed as an Information Retrieval coursework assignment by student `S20240010254`.
