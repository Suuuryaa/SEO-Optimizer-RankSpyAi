def build_benchmark_summary(primary_row, benchmark_rows):
    summary = {}

    primary_rank = primary_row.get("SERP Rank", "N/A")
    primary_score = primary_row.get("SEO Score", 0)

    summary["primary_rank"] = primary_rank
    summary["primary_score"] = primary_score

    competitors = [
        r for r in benchmark_rows
        if r.get("Role") == "Direct Competitor"
    ]

    if competitors:
        best_comp = max(competitors, key=lambda x: x.get("SEO Score", 0))
        summary["top_competitor"] = best_comp.get("Venue Name", "N/A")
        summary["top_comp_score"] = best_comp.get("SEO Score", 0)

        if primary_score < best_comp.get("SEO Score", 0):
            summary["gap"] = "On-page SEO strength"
        else:
            summary["gap"] = "SERP ranking position"

    else:
        summary["top_competitor"] = "N/A"
        summary["top_comp_score"] = 0
        summary["gap"] = "More competitor data needed"

    return summary