(() => {
  const toastRegion = document.querySelector(".toast-region");
  let toastTimer;

  function showToast(message) {
    if (!toastRegion) {
      return;
    }

    toastRegion.textContent = message;
    toastRegion.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toastRegion.classList.remove("is-visible");
    }, 2800);
  }

  const notificationButton = document.querySelector("[data-notifications-toggle]");
  const notificationPanel = document.querySelector("#notification-panel");
  const notificationList = document.querySelector("[data-notification-list]");
  const notificationSummary = document.querySelector("[data-notification-summary]");
  const notificationCount = document.querySelector(".notification-count");
  const notificationDot = document.querySelector(".notification-dot");
  const markAllReadButton = document.querySelector("[data-notifications-read-all]");

  function setUnreadCount(count) {
    const unreadCount = Number(count) || 0;
    if (notificationCount) {
      notificationCount.textContent = unreadCount > 99 ? "99+" : String(unreadCount);
      notificationCount.hidden = unreadCount === 0;
    }
    if (notificationDot) {
      notificationDot.hidden = unreadCount === 0;
    }
    notificationButton?.setAttribute(
      "aria-label",
      unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"
    );
    if (markAllReadButton) {
      markAllReadButton.hidden = unreadCount === 0;
    }
  }

  function formatNotificationDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Recently";
    }
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  function renderNotifications(notifications) {
    if (!notificationList) {
      return;
    }
    notificationList.replaceChildren();

    if (!notifications.length) {
      const empty = document.createElement("p");
      empty.className = "notification-empty";
      empty.textContent = "You’re all caught up.";
      notificationList.append(empty);
      return;
    }

    notifications.forEach((notification) => {
      const item = document.createElement("article");
      item.className = `notification-item${notification.is_read ? "" : " is-unread"}`;

      const marker = document.createElement("span");
      marker.className = "notification-item-marker";
      marker.setAttribute("aria-hidden", "true");

      const content = document.createElement("div");
      content.className = "notification-item-content";
      const message = document.createElement("p");
      message.textContent = notification.message;
      const timestamp = document.createElement("time");
      timestamp.dateTime = notification.timestamp;
      timestamp.textContent = formatNotificationDate(notification.timestamp);
      content.append(message, timestamp);
      item.append(marker, content);

      if (!notification.is_read) {
        const markRead = document.createElement("button");
        markRead.className = "notification-mark-read";
        markRead.type = "button";
        markRead.textContent = "Mark read";
        markRead.setAttribute("aria-label", `Mark notification read: ${notification.message}`);
        markRead.addEventListener("click", () => markNotificationRead(notification.id));
        item.append(markRead);
      }
      notificationList.append(item);
    });
  }

  async function loadNotifications() {
    if (!notificationList) {
      return;
    }
    try {
      const response = await fetch("/api/notifications", {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Notification request failed with status ${response.status}`);
      }
      const data = await response.json();
      setUnreadCount(data.unread_count);
      renderNotifications(data.notifications);
      if (notificationSummary) {
        notificationSummary.textContent = data.unread_count
          ? `${data.unread_count} unread`
          : "You’re all caught up";
      }
    } catch (error) {
      console.error("Could not load notifications.", error);
      if (notificationSummary) {
        notificationSummary.textContent = "Could not load notifications.";
      }
      if (notificationList) {
        notificationList.replaceChildren();
        const retry = document.createElement("button");
        retry.className = "notification-retry";
        retry.type = "button";
        retry.textContent = "Try again";
        retry.addEventListener("click", loadNotifications);
        notificationList.append(retry);
      }
    }
  }

  async function markNotificationRead(id) {
    try {
      const response = await fetch(`/api/notifications/${encodeURIComponent(id)}/read`, {
        method: "POST",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Mark-read request failed with status ${response.status}`);
      }
      await loadNotifications();
    } catch (error) {
      console.error("Could not mark notification as read.", error);
      showToast("Could not update this notification. Please try again.");
    }
  }

  notificationButton?.addEventListener("click", async () => {
    const isOpen = notificationButton.getAttribute("aria-expanded") === "true";
    notificationButton.setAttribute("aria-expanded", String(!isOpen));
    if (notificationPanel) {
      notificationPanel.hidden = isOpen;
    }
    if (!isOpen) {
      await loadNotifications();
    }
  });

  markAllReadButton?.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/notifications/read-all", {
        method: "POST",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Mark-all-read request failed with status ${response.status}`);
      }
      await loadNotifications();
    } catch (error) {
      console.error("Could not mark all notifications as read.", error);
      showToast("Could not update notifications. Please try again.");
    }
  });

  document.addEventListener("click", (event) => {
    if (
      notificationPanel &&
      notificationButton &&
      !notificationPanel.hidden &&
      !event.target.closest(".notification-menu")
    ) {
      notificationPanel.hidden = true;
      notificationButton.setAttribute("aria-expanded", "false");
    }
  });

  if (notificationList) {
    loadNotifications();
    window.setInterval(() => {
      if (!document.hidden) {
        loadNotifications();
      }
    }, 30000);
  }

  document.querySelectorAll("[data-global-search]").forEach((input) => {
    input.addEventListener("input", () => {
      const query = input.value.trim().toLocaleLowerCase();
      const tables = [...document.querySelectorAll(".data-table")];

      if (tables.length) {
        tables.forEach((table) => {
          table.querySelectorAll("tbody tr").forEach((row) => {
            row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
          });
        });
      } else {
        document.querySelectorAll(".dashboard-grid .card, .dashboard-grid .metric-card, .overview-grid .card, .activity-card").forEach((card) => {
          card.hidden = query.length > 0 && !card.textContent.toLocaleLowerCase().includes(query);
        });
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      document.querySelector("[data-global-search]")?.focus();
    }
  });

  document.querySelectorAll("[data-toast]").forEach((button) => {
    button.addEventListener("click", () => showToast(button.dataset.toast));
  });

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.openDialog)?.showModal());
  });

  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
  });

  document.querySelectorAll(".form-dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });
  });

  function updateResultCount(table) {
    if (!table?.tBodies[0]) {
      return;
    }
    const counter = document.querySelector("[data-result-count]");
    if (counter) {
      const visibleCount = [...table.tBodies[0].rows].filter((row) => !row.hidden).length;
      const label = table.id === "customers-table" ? "customers" : table.id === "transactions-table" ? "transactions" : "products";
      counter.textContent = `Showing ${visibleCount} ${label}`;
    }
  }

  document.querySelector("[data-filter-status]")?.addEventListener("change", (event) => {
    const filter = event.currentTarget.value.toLocaleLowerCase();
    document.querySelectorAll("#stock-table tbody tr").forEach((row) => {
      row.hidden = filter.length > 0 && !row.querySelector(".status-pill")?.textContent.toLocaleLowerCase().includes(filter);
    });
    updateResultCount(document.querySelector("#stock-table"));
  });

  document.querySelectorAll(".data-table th").forEach((header, columnIndex) => {
    header.tabIndex = 0;
    header.setAttribute("role", "button");
    header.title = "Sort by this column";
    const sortRows = () => {
      const table = header.closest("table");
      const tbody = table?.tBodies[0];
      if (!tbody) {
        return;
      }
      const ascending = header.dataset.sortDirection !== "ascending";
      table.querySelectorAll("th").forEach((cell) => delete cell.dataset.sortDirection);
      header.dataset.sortDirection = ascending ? "ascending" : "descending";
      [...tbody.rows]
        .sort((left, right) => {
          const a = left.cells[columnIndex]?.textContent.trim() || "";
          const b = right.cells[columnIndex]?.textContent.trim() || "";
          return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }) * (ascending ? 1 : -1);
        })
        .forEach((row) => tbody.append(row));
    };
    header.addEventListener("click", sortRows);
    header.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        sortRows();
      }
    });
  });

  document.querySelectorAll("[data-export-table]").forEach((button) => {
    button.addEventListener("click", () => {
      const table = document.getElementById(button.dataset.exportTable);
      if (!table) {
        showToast("Could not find a table to export.");
        return;
      }

      const csv = [...table.rows]
        .map((row) => [...row.cells].map((cell) => {
          const value = cell.textContent.trim().replace(/\s+/g, " ");
          return `"${value.replace(/"/g, '""')}"`;
        }).join(","))
        .join("\r\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${table.id}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      showToast("CSV download started.");
    });
  });

})();
