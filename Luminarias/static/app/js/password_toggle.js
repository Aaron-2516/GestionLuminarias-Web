document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
        const field = button.closest(".password-field");
        const input = field.querySelector("input");
        const isHidden = input.type === "password";

        input.type = isHidden ? "text" : "password";
        button.textContent = isHidden ? "Ocultar" : "Ver";
        button.setAttribute(
            "aria-label",
            isHidden ? "Ocultar contrasena" : "Mostrar contrasena"
        );
    });
});
