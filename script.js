const header = document.querySelector("[data-header]");
const menuButton = document.querySelector("[data-menu-button]");
const navigation = document.querySelector("[data-nav]");
const navigationLinks = navigation?.querySelectorAll("a") ?? [];
const dashboardTabs = [...document.querySelectorAll("[data-dashboard-tab]")];
const dashboardPanel = document.querySelector("#dashboard-panel");
const dashboardImage = document.querySelector("[data-dashboard-image]");
const dashboardTitle = document.querySelector("[data-dashboard-title]");
const dashboardDescription = document.querySelector("[data-dashboard-description]");
const dashboardCounter = document.querySelector("[data-dashboard-counter]");
const year = document.querySelector("[data-year]");

const setHeaderState = () => {
  header?.classList.toggle("is-scrolled", window.scrollY > 12);
};

const closeMenu = () => {
  if (!menuButton || !navigation) return;
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.querySelector(".sr-only").textContent = "Abrir navegación";
  navigation.classList.remove("is-open");
  document.body.classList.remove("menu-open");
};

menuButton?.addEventListener("click", () => {
  if (!navigation) return;
  const isOpen = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isOpen));
  menuButton.querySelector(".sr-only").textContent = isOpen
    ? "Abrir navegación"
    : "Cerrar navegación";
  navigation.classList.toggle("is-open", !isOpen);
  document.body.classList.toggle("menu-open", !isOpen);
});

navigationLinks.forEach((link) => link.addEventListener("click", closeMenu));

window.addEventListener("scroll", setHeaderState, { passive: true });
setHeaderState();

const activateDashboard = (selectedTab) => {
  if (
    !dashboardPanel ||
    !dashboardImage ||
    !dashboardTitle ||
    !dashboardDescription ||
    !dashboardCounter
  ) {
    return;
  }

  const selectedIndex = dashboardTabs.indexOf(selectedTab);
  dashboardPanel.classList.add("is-changing");

  dashboardTabs.forEach((tab) => {
    const isSelected = tab === selectedTab;
    tab.classList.toggle("is-active", isSelected);
    tab.setAttribute("aria-selected", String(isSelected));
    tab.tabIndex = isSelected ? 0 : -1;
  });

  window.setTimeout(() => {
    dashboardImage.src = selectedTab.dataset.image;
    dashboardImage.alt = selectedTab.dataset.alt;
    dashboardTitle.textContent = selectedTab.dataset.title;
    dashboardDescription.textContent = selectedTab.dataset.description;
    dashboardCounter.textContent = `${String(selectedIndex + 1).padStart(2, "0")} / 03`;
    dashboardPanel.setAttribute("aria-labelledby", selectedTab.id);
    dashboardPanel.classList.remove("is-changing");
  }, 140);
};

dashboardTabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateDashboard(tab));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();

    let nextIndex = index;
    if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + dashboardTabs.length) % dashboardTabs.length;
    } else if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % dashboardTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = dashboardTabs.length - 1;
    }

    dashboardTabs[nextIndex].focus();
    activateDashboard(dashboardTabs[nextIndex]);
  });
});

if (year) {
  year.textContent = String(new Date().getFullYear());
}
