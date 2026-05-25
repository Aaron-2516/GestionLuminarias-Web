document.addEventListener("DOMContentLoaded", () => {
    const abrirModal = document.getElementById("abrirModal");
    const cerrarModal = document.getElementById("cerrarModal");
    const contenedorModal = document.getElementById("contenedorModal");

    if (!abrirModal || !cerrarModal || !contenedorModal) {
        return;
    }

    abrirModal.addEventListener("click", () => {
        contenedorModal.classList.add("mostrar");
    });

    cerrarModal.addEventListener("click", () => {
        contenedorModal.classList.remove("mostrar");
    });

    contenedorModal.addEventListener("click", (event) => {
        if (event.target === contenedorModal) {
            contenedorModal.classList.remove("mostrar");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            contenedorModal.classList.remove("mostrar");
        }
    });
});