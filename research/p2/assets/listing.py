def coverage(dist, n, p, data, rng):
    draw, mu = _sampler(dist, data)
    x = draw(rng, (p.n_sim, n))
    mean, sd = x.mean(axis=1), x.std(axis=1, ddof=1)
    half = stats.t.ppf(1 - p.alpha / 2, n - 1) * sd / np.sqrt(n)
    return float(np.mean(np.abs(mean - mu) <= half))
