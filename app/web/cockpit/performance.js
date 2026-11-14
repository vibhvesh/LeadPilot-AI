/* Admin link from the flight deck to the performance page. Hidden for every other role. */
(function (root) {
  root.CockpitPerformance = {
    link: function () {
      const role = document.documentElement.dataset.role || "";
      if (role !== "admin" && role !== "super_admin") return "";
      return '<a class="cockpit-perf" href="/admin/performance">Performance</a>';
    },
  };
})(window);
