document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".favorite-toggle-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector(".favorite-button");
      const icon = form.querySelector(".favorite-icon");
      const formData = new FormData(form);
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
          headers: {
            Accept: "application/json",
            "X-Requested-With": "fetch",
          },
        });
        if (!response.ok) {
          form.submit();
          return;
        }
        const data = await response.json();
        button.classList.toggle("is-favorite", data.favorited);
        icon.textContent = data.favorited ? "♥" : "♡";
      } catch (_error) {
        form.submit();
      }
    });
  });
});
