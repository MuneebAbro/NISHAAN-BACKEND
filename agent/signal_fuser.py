def fuse_signals(weather, social, traffic):
    # Group social signals by neighborhood
    neighborhood_reports = {}
    for r in social:
        n = r["neighborhood"]
        if n not in neighborhood_reports:
            neighborhood_reports[n] = []
        neighborhood_reports[n].append(r)
        
    contexts = []
    
    for n, reports in neighborhood_reports.items():
        avg_credibility = sum(r["credibility"] for r in reports) / len(reports)
        
        context = {
            "neighborhood": n,
            "weather": weather,
            "traffic": traffic.get(n, {}),
            "social_reports": reports,
            "social_credibility": avg_credibility,
            "num_reports": len(reports)
        }
        contexts.append(context)
        
    return contexts
