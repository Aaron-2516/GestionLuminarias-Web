document.addEventListener("DOMContentLoaded", function () {

    const modalAgregar = document.getElementById("contenedorModalAgregar");
    const modalEditar = document.getElementById("contenedorModalEditar");

    const abrirModalAgregar = document.getElementById("abrirModalAgregar");
    const cerrarModalAgregar = document.getElementById("cerrarModalAgregar");
    const cerrarModalEditar = document.getElementById("cerrarModalEditar");

    function abrirModal(modal) {
        if (modal) {
            modal.classList.add("mostrar");
        }
    }

    function cerrarModal(modal) {
        if (modal) {
            modal.classList.remove("mostrar");
        }
    }

    function asignarValor(id, valor) {
        const elemento = document.getElementById(id);

        if (elemento) {
            elemento.value = valor || "";
        }
    }

    // ABRIR MODAL AGREGAR
    if (abrirModalAgregar) {
        abrirModalAgregar.addEventListener("click", function () {
            abrirModal(modalAgregar);
        });
    }

    // CERRAR MODAL AGREGAR
    if (cerrarModalAgregar) {
        cerrarModalAgregar.addEventListener("click", function () {
            cerrarModal(modalAgregar);
        });
    }

    // CERRAR MODAL EDITAR
    if (cerrarModalEditar) {
        cerrarModalEditar.addEventListener("click", function () {
            cerrarModal(modalEditar);
        });
    }

    // BOTONES EDITAR
    document.querySelectorAll(".btn-editar").forEach(function (boton) {

        boton.addEventListener("click", function () {

            // CAMPO COMÚN PARA TÉCNICOS Y REDES
            asignarValor("editar_id", this.dataset.id);

            // =========================
            // EDITAR TÉCNICO
            // =========================
            asignarValor("editar_nombre_usuario", this.dataset.nombre);
            asignarValor("editar_apellido_usuario", this.dataset.apellido);
            asignarValor("editar_telefono", this.dataset.telefono);
            asignarValor("editar_estado", this.dataset.estado);
            asignarValor("editar-zona-select", this.dataset.zona);

            // =========================
            // EDITAR RED
            // =========================
            asignarValor("editar_nombre_red", this.dataset.nombre);
            asignarValor("editar_voltaje", this.dataset.voltaje);

            abrirModal(modalEditar);

        });

    });

    // CERRAR MODALES HACIENDO CLICK AFUERA
    window.addEventListener("click", function (event) {

        if (modalAgregar && event.target === modalAgregar) {
            cerrarModal(modalAgregar);
        }

        if (modalEditar && event.target === modalEditar) {
            cerrarModal(modalEditar);
        }

    });

});