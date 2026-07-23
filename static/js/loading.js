
(function () {
  "use strict";

  function getOverlay() {
    return document.getElementById("loading-overlay");
  }

  function showLoading() {
    const overlay = getOverlay();
    if (overlay) overlay.classList.add("ativo");
  }

  function hideLoading() {
    const overlay = getOverlay();
    if (overlay) overlay.classList.remove("ativo");
  }


  window.CuideLoading = { show: showLoading, hide: hideLoading };


  window.addEventListener("DOMContentLoaded", () => {
    
    setTimeout(hideLoading, 150);
  });


  window.addEventListener("load", hideLoading);

  document.addEventListener("click", (ev) => {
    const link = ev.target.closest("a[href]");
    if (!link) return;

    const href = link.getAttribute("href");
    const abreEmNovaAba = link.target === "_blank";
    const ehAncora = href && href.startsWith("#");
    const ehExterno = href && /^https?:\/\//i.test(href) && !href.startsWith(window.location.origin);
    const ehAcaoJs = href === "javascript:void(0)" || link.hasAttribute("data-no-loading");

    if (!href || abreEmNovaAba || ehAncora || ehExterno || ehAcaoJs) return;

    showLoading();
  });

  
  document.addEventListener("submit", (ev) => {
    const form = ev.target;
    if (form && !form.hasAttribute("data-no-loading")) {
      showLoading();
    }
  });

  const fetchOriginal = window.fetch;
  window.fetch = function (...args) {
    showLoading();
    return fetchOriginal.apply(this, args)
      .then((resp) => {
        hideLoading();
        return resp;
      })
      .catch((err) => {
        hideLoading();
        throw err;
      });
  };
})();
