def generate_strategic_insights(primary_row, benchmark_rows, keyword):
    insights = []

    primary_name = primary_row.get("Venue Name", "Primary Venue")
    primary_rank = primary_row.get("SERP Rank", "N/A")
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
                f"{primary_name} ranks #{primary_rank} in Google and has a stronger SEO score ({primary_score}) than the top external competitor {best_competitor_name} ({best_competitor_score})."
            )
        elif primary_score < best_competitor_score:
            insights.append(
                f"{primary_name} ranks #{primary_rank} in Google but is outperformed on SEO score by {best_competitor_name}, which may indicate stronger on-page optimization."
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

    if competitor_rows:
        higher_ranked = [
            row for row in competitor_rows
            if row.get("SERP Rank", 999) < primary_rank
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