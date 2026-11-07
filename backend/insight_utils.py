def generate_strategic_insights(primary_row, benchmark_rows, keyword):
    insights = []

    primary_name = primary_row.get("Venue Name", "Primary Venue")
    primary_rank = primary_row.get("SERP Rank")   # int = measured position; None = not in top 30; "unknown" = not checked
    if isinstance(primary_rank, int):
        rank_phrase = f"ranks #{primary_rank} in Google for \"{keyword}\""
    elif primary_rank is None:
        rank_phrase = f"does not appear in Google's top 30 for \"{keyword}\""
    else:
        rank_phrase = None
    primary_score = primary_row.get("SEO Score", 0)
    primary_keyword_count = primary_row.get("Keyword Count", 0)
    primary_word_count = primary_row.get("Word Count", 0)
    primary_alt = primary_row.get("Images Missing ALT", 0)

    competitor_rows = [
        row for row in benchmark_rows
        if row.get("Role") == "Direct Competitor"
    ]

    if competitor_rows:
        best_competitor = max(competitor_rows, key=lambda x: x.get("SEO Score", 0))
        best_competitor_name = best_competitor.get("Venue Name", "Competitor")
        best_competitor_score = best_competitor.get("SEO Score", 0)
        best_competitor_rank = best_competitor.get("SERP Rank", "N/A")

        if primary_score > best_competitor_score:
            insights.append(
                (f"{primary_name} {rank_phrase} and has" if rank_phrase else f"{primary_name} has")
                + f" a stronger SEO score ({primary_score}) than the top external competitor {best_competitor_name} ({best_competitor_score})."
            )
        elif primary_score < best_competitor_score:
            insights.append(
                (f"{primary_name} {rank_phrase} but is" if rank_phrase else f"{primary_name} is")
                + f" outperformed on SEO score by {best_competitor_name}, which may indicate stronger on-page optimization."
            )
        else:
            insights.append(
                f"{primary_name} and {best_competitor_name} currently have similar SEO scores, so ranking differences may come from authority, backlinks, or local relevance."
            )

    if primary_keyword_count == 0:
        insights.append(
            f"The exact target keyword '{keyword}' is not used in the main page content, which is likely limiting relevance signals for search engines."
        )
    elif primary_keyword_count < 3:
        insights.append(
            f"The target keyword '{keyword}' appears only a few times, so keyword targeting could be strengthened."
        )
    else:
        insights.append(
            f"The page uses the target keyword '{keyword}' in content, which supports topical relevance."
        )

    if primary_word_count >= 700:
        insights.append(
            f"{primary_name} has strong content depth ({primary_word_count} words), which is a positive signal compared with thinner competitor pages."
        )
    elif primary_word_count < 300:
        insights.append(
            f"{primary_name} has relatively thin content ({primary_word_count} words), which may weaken SEO competitiveness."
        )

    if primary_alt > 10:
        insights.append(
            f"The page has a high number of images missing ALT text ({primary_alt}), which creates both SEO and accessibility weaknesses."
        )
    elif primary_alt == 0:
        insights.append(
            "Image ALT coverage is strong, which supports accessibility and image SEO."
        )

    # Compare positions only when they were measured in Google
    ranked = [r for r in competitor_rows if isinstance(r.get("SERP Rank"), int)]
    if ranked and (isinstance(primary_rank, int) or primary_rank is None):
        higher_ranked = [
            row for row in ranked
            if primary_rank is None or row["SERP Rank"] < primary_rank
        ]

        if higher_ranked:
            insights.append(
                f"There are direct competitors ranking above {primary_name}, so the immediate opportunity is to improve keyword placement, technical quality, and local relevance signals."
            )
        else:
            insights.append(
                f"{primary_name} is ahead of the direct competitors shown in the current SERP sample, which suggests relatively strong competitive positioning."
            )

    return insights