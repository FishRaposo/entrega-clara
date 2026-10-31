document.querySelectorAll(".tab-switcher").forEach((switcher) => {
  const tabs = switcher.querySelectorAll(".tab");
  const primaryBtn = switcher.closest(".phone-screen")?.querySelector(".btn-primary");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");

      if (primaryBtn) {
        primaryBtn.textContent = tab.dataset.tab === "signup" ? "Cadastrar" : "Entrar";
      }
    });
  });
});
