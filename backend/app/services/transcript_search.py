"""
ClipPilot AI - Meaning-Based Transcript Search & Ambiguity Resolution (Feature 10)
===================================================================================
Provides semantic matching of natural language references against video transcripts.
Enables queries like "pricing" to match transcript speech about "cost", "fees", or "subscriptions".

Guarantees:
1. Always calculates a confidence/relevance score for candidate matches.
2. Formats candidate matches with passage text, timestamps, and confidence information.
3. Requires user confirmation before applying cuts to semantic search matches.
4. Never silently cuts a low-confidence or ambiguous match.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class TranscriptSearchEngine:
    """
    Semantic search engine for video transcripts.
    Uses concept expansion, synonym clustering, and phrase similarity scoring.
    """

    # Semantic concept ontology with weighted related terms
    CONCEPT_ONTOLOGY: Dict[str, Dict[str, float]] = {
        "pricing": {
            "pricing": 1.0,
            "price": 0.95,
            "cost": 0.95,
            "costs": 0.95,
            "expensive": 0.90,
            "cheap": 0.85,
            "affordable": 0.85,
            "fee": 0.90,
            "fees": 0.90,
            "subscription": 0.95,
            "subscribe": 0.85,
            "tier": 0.85,
            "plan": 0.85,
            "plans": 0.85,
            "billing": 0.90,
            "bill": 0.85,
            "dollar": 0.85,
            "dollars": 0.85,
            "payment": 0.90,
            "charge": 0.80,
            "discount": 0.85,
            "rate": 0.80,
            "rates": 0.80,
            "invoice": 0.85,
            "money": 0.75,
            "pay": 0.80,
        },
        "intro": {
            "intro": 1.0,
            "introduction": 0.95,
            "hello": 0.90,
            "hi": 0.85,
            "welcome": 0.90,
            "hey": 0.85,
            "start": 0.80,
            "beginning": 0.80,
            "kick off": 0.80,
            "overview": 0.75,
        },
        "outro": {
            "outro": 1.0,
            "conclusion": 0.95,
            "summary": 0.85,
            "wrap up": 0.90,
            "goodbye": 0.90,
            "bye": 0.85,
            "thanks for watching": 0.95,
            "thank you": 0.85,
            "thanks": 0.80,
            "see you next time": 0.95,
            "ending": 0.85,
            "sign off": 0.90,
        },
        "features": {
            "features": 1.0,
            "feature": 0.95,
            "capabilities": 0.90,
            "capability": 0.90,
            "tools": 0.85,
            "tool": 0.85,
            "functionality": 0.90,
            "functions": 0.85,
            "demo": 0.80,
            "walkthrough": 0.85,
            "showcase": 0.85,
        },
        "boring": {
            "boring": 1.0,
            "dull": 0.90,
            "filler": 0.90,
            "rambling": 0.85,
            "pause": 0.85,
            "pauses": 0.85,
            "silence": 0.90,
            "dead air": 0.95,
            "um": 0.75,
            "uh": 0.75,
            "hesitation": 0.80,
        }
    }

    @classmethod
    def get_query_terms(cls, query: str) -> Dict[str, float]:
        """
        Extracts search terms from query and expands with semantic concepts.
        Returns a dict of term -> relevance weight.
        """
        q_lower = query.strip().lower()
        # Clean query
        q_clean = re.sub(r"[^\w\s]", " ", q_lower)
        tokens = [t for t in q_clean.split() if len(t) > 2 and t not in [
            "the", "about", "part", "section", "talking", "mentioned", "where", "says",
            "said", "remove", "cut", "delete", "slice", "clip", "video", "and", "from"
        ]]

        term_weights: Dict[str, float] = {}

        # 1. Direct tokens have weight 1.0
        for tok in tokens:
            term_weights[tok] = 1.0

        # 2. Check each known concept
        for concept, syn_dict in cls.CONCEPT_ONTOLOGY.items():
            # If the concept or any of its main keywords is in the query
            matched_concept = False
            if concept in q_lower or any(k in q_lower.split() for k in syn_dict.keys()):
                matched_concept = True

            if matched_concept:
                for syn, wt in syn_dict.items():
                    if syn not in term_weights or term_weights[syn] < wt:
                        term_weights[syn] = wt

        return term_weights

    @classmethod
    def search_transcript(
        cls,
        query: str,
        transcript_segments: List[Dict[str, Any]],
        threshold: float = 0.50
    ) -> List[Dict[str, Any]]:
        """
        Searches transcript segments for semantic relevance to the query.
        Returns ranked list of candidate matches:
        [
          {
            "passage": str,
            "start": float,
            "end": float,
            "confidence": float,
            "matched_terms": List[str],
            "query": str
          },
          ...
        ]
        """
        if not transcript_segments or not query.strip():
            return []

        term_weights = cls.get_query_terms(query)
        if not term_weights:
            return []

        candidates: List[Dict[str, Any]] = []

        for seg in transcript_segments:
            text = str(seg.get("text", "")).strip()
            if not text:
                continue

            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", 0.0))
            text_lower = text.lower()
            text_tokens = set(re.findall(r"\w+", text_lower))

            matched_terms: List[str] = []
            max_term_wt = 0.0
            total_score = 0.0

            for term, weight in term_weights.items():
                if " " in term:
                    # Multi-word phrase
                    if term in text_lower:
                        matched_terms.append(term)
                        total_score += weight * 1.5
                        if weight > max_term_wt:
                            max_term_wt = weight
                else:
                    if term in text_tokens:
                        matched_terms.append(term)
                        total_score += weight
                        if weight > max_term_wt:
                            max_term_wt = weight

            if matched_terms:
                # Calculate confidence normalized to [0.0, 1.0]
                # High base on max term weight, boosted by multiple matches
                confidence = min(0.99, max_term_wt * 0.85 + (len(matched_terms) - 1) * 0.05)
                confidence = round(confidence, 2)

                if confidence >= threshold:
                    candidates.append({
                        "text": text,
                        "passage": text,
                        "start": round(seg_start, 2),
                        "end": round(seg_end, 2),
                        "duration": round(max(0.0, seg_end - seg_start), 2),
                        "confidence": confidence,
                        "matched_terms": list(set(matched_terms)),
                        "query": query.strip()
                    })

        # Sort candidates by confidence descending, then by duration
        candidates.sort(key=lambda c: (-c["confidence"], c["start"]))
        return candidates

    @classmethod
    def get_sample_transcript(cls, duration: float = 10.0) -> List[Dict[str, Any]]:
        """
        Provides a realistic, structured timestamped transcript for testing
        and default synthetic demonstration assets.
        Includes speech about pricing, costs, features, and intro.
        """
        if duration <= 10.0:
            return [
                {
                    "text": "Welcome to ClipPilot AI, the prompt-to-video editing engine.",
                    "start": 0.5,
                    "end": 3.0,
                    "words": [
                        {"word": "Welcome", "start": 0.5, "end": 0.9},
                        {"word": "to", "start": 0.9, "end": 1.1},
                        {"word": "ClipPilot", "start": 1.1, "end": 1.6},
                        {"word": "AI", "start": 1.6, "end": 1.9},
                        {"word": "the", "start": 2.0, "end": 2.2},
                        {"word": "prompt-to-video", "start": 2.2, "end": 2.6},
                        {"word": "editing", "start": 2.6, "end": 2.8},
                        {"word": "engine", "start": 2.8, "end": 3.0},
                    ]
                },
                {
                    "text": "Let's review the monthly cost and subscription pricing tiers.",
                    "start": 3.5,
                    "end": 6.5,
                    "words": [
                        {"word": "Let's", "start": 3.5, "end": 3.8},
                        {"word": "review", "start": 3.8, "end": 4.1},
                        {"word": "the", "start": 4.1, "end": 4.3},
                        {"word": "monthly", "start": 4.3, "end": 4.7},
                        {"word": "cost", "start": 4.7, "end": 5.1},
                        {"word": "and", "start": 5.1, "end": 5.3},
                        {"word": "subscription", "start": 5.3, "end": 5.9},
                        {"word": "pricing", "start": 5.9, "end": 6.2},
                        {"word": "tiers", "start": 6.2, "end": 6.5},
                    ]
                },
                {
                    "text": "Thank you for watching and see you in the next tutorial.",
                    "start": 7.0,
                    "end": 9.5,
                    "words": [
                        {"word": "Thank", "start": 7.0, "end": 7.3},
                        {"word": "you", "start": 7.3, "end": 7.5},
                        {"word": "for", "start": 7.5, "end": 7.7},
                        {"word": "watching", "start": 7.7, "end": 8.2},
                        {"word": "and", "start": 8.2, "end": 8.4},
                        {"word": "see", "start": 8.4, "end": 8.7},
                        {"word": "you", "start": 8.7, "end": 8.9},
                        {"word": "in", "start": 8.9, "end": 9.1},
                        {"word": "the", "start": 9.1, "end": 9.2},
                        {"word": "next", "start": 9.2, "end": 9.4},
                        {"word": "tutorial", "start": 9.4, "end": 9.5},
                    ]
                }
            ]
        else:
            return [
                {
                    "text": "Welcome to ClipPilot AI creative studio walkthrough.",
                    "start": 0.5,
                    "end": 4.0,
                    "words": []
                },
                {
                    "text": "Now let's examine the total cost of ownership and subscription pricing tiers.",
                    "start": 4.5,
                    "end": 9.0,
                    "words": []
                },
                {
                    "text": "We will explore editing features, audio sync, and video speed adjustments.",
                    "start": 9.5,
                    "end": 15.0,
                    "words": []
                },
                {
                    "text": "Thank you for joining our product demo and tutorial session.",
                    "start": 15.5,
                    "end": 19.5,
                    "words": []
                }
            ]
