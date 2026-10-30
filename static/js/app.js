// app.js - sidebar toggle, submenu, profile dropdown, flash messages
document.addEventListener("DOMContentLoaded", function () {
  var sidebar = document.getElementById("sidebar");
  var overlay = document.getElementById("overlay");
  var menuBtn = document.getElementById("menuBtn");
  var profileBtn = document.getElementById("profileBtn");
  var profileMenu = document.getElementById("profileMenu");

  // Hamburger button opens/closes the sidebar on small screens
  function toggleSidebar() {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
  }
  if (menuBtn) menuBtn.addEventListener("click", toggleSidebar);
  if (overlay) overlay.addEventListener("click", toggleSidebar);

  // Expand / collapse the "Tree Management" submenu
  document.querySelectorAll("[data-submenu]").forEach(function (button) {
    button.addEventListener("click", function () {
      var menu = document.getElementById(button.getAttribute("data-submenu"));
      menu.classList.toggle("open");
    });
  });

  // Profile dropdown
  if (profileBtn) {
    profileBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      profileMenu.classList.toggle("open");
    });
    document.addEventListener("click", function () {
      profileMenu.classList.remove("open");
    });
  }

  // Flash messages: close button + auto-hide after 6 seconds
  document.querySelectorAll(".flash").forEach(function (box) {
    var close = box.querySelector(".flash-close");
    if (close) close.addEventListener("click", function () { box.remove(); });
    setTimeout(function () { box.remove(); }, 6000);
  });
});