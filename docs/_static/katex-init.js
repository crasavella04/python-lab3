// Рендер формул KaTeX. Разметку \( \) и \[ \] формирует Sphinx (sphinx.ext.mathjax),
// KaTeX лежит в _static/katex — формулы не зависят от внешних CDN.
document.addEventListener("DOMContentLoaded", () => {
  renderMathInElement(document.body, {
    delimiters: [
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
    ],
    throwOnError: false,
  });
});
