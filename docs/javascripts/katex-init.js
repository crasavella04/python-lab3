// Рендер формул, размеченных pymdownx.arithmatex (generic: true).
// KaTeX лежит в docs/assets/katex, поэтому формулы не зависят от внешних CDN.
// document$ — наблюдаемый объект Material: срабатывает и при навигации navigation.instant.
document$.subscribe(({ body }) => {
  renderMathInElement(body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
    ],
  });
});
