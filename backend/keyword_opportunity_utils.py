import re
from collections import Counter

STOPWORDS = {
    "about", "above", "after", "again", "against", "almost", "also", "always",
    "among", "another", "around", "because", "before", "being", "below", "between",
    "both", "bring", "came", "cannot", "come", "coming", "could", "customer",
    "customers", "daily", "detail", "details", "doing", "during", "each", "early",
    "enough", "every", "everyone", "everything", "experience", "experiences",
    "family", "first", "found", "from", "further", "great", "have", "having",
    "here", "into", "just", "like", "long", "made", "make", "many", "maybe",
    "more", "most", "much", "need", "next", "night", "other", "our", "over",
    "people", "place", "places", "plan", "really", "save", "should", "show",
    "small", "some", "still", "such", "take", "than", "that", "their", "them",
    "there", "these", "they", "this", "those", "through", "very", "want", "week",
    "well", "were", "what", "when", "where", "which", "while", "with", "would",
    "your", "you", "open", "news", "person", "ages", "race", "fullsize"
}

WEAK_SINGLE_WORDS = {
    "today", "story", "stories", "thing", "things", "people", "person", "place",
    "places", "group", "groups", "years", "months", "weeks", "local", "general",
    "feature", "features", "content", "section", "sections"
}


def tokenize(text):
    return re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())


def clean_words(words):
    cleaned = []
    for word in words:
        if word in STOPWORDS:
            continue
        if len(word) < 4:
            continue
        cleaned.append(word)
    return cleaned


def extract_unigrams(text):
    words = tokenize(text)
    words = clean_words(words)
    return words


def extract_bigrams(text):
    words = extract_unigrams(text)
    bigrams = []

    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i+1]}"
        bigrams.append(phrase)

    return bigrams


def is_useful_term(term):
    words = term.split()

    # Prefer 2-word phrases because they are more meaningful across industries
    if len(words) == 2:
        # reject repeated junk like "days days"
        if words[0] == words[1]:
            return False
        return True

    # For 1-word terms, keep only stronger standalone words
    if len(words) == 1:
        word = words[0]

        if word in WEAK_SINGLE_WORDS:
            return False

        # prefer longer and more specific single words
        if len(word) >= 6:
            return True

        # optionally allow certain strong word endings
        if word.endswith("ing") or word.endswith("ion") or word.endswith("ment"):
            return True

        return False

    return False


def find_keyword_opportunities(primary_text, competitor_texts, top_n=15):
    primary_unigrams = set(extract_unigrams(primary_text))
    primary_bigrams = set(extract_bigrams(primary_text))

    competitor_unigram_counter = Counter()
    competitor_bigram_counter = Counter()

    for text in competitor_texts:
        competitor_unigram_counter.update(extract_unigrams(text))
        competitor_bigram_counter.update(extract_bigrams(text))

    opportunities = []

    # First prefer repeated 2-word phrases
    for phrase, freq in competitor_bigram_counter.most_common():
        if phrase in primary_bigrams:
            continue
        if freq < 2:
            continue
        if not is_useful_term(phrase):
            continue

        opportunities.append((phrase, freq, "Phrase"))

        if len(opportunities) >= top_n:
            return opportunities

    # Then add stronger repeated single terms
    for word, freq in competitor_unigram_counter.most_common():
        if word in primary_unigrams:
            continue
        if freq < 3:
            continue
        if not is_useful_term(word):
            continue

        opportunities.append((word, freq, "Term"))

        if len(opportunities) >= top_n:
            break

    return opportunities