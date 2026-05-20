function mostrarDetalle(titulo, texto) {
    const panel = document.getElementById("panelDetalle");
    const detalleTitulo = document.getElementById("detalleTitulo");
    const detalleTexto = document.getElementById("detalleTexto");

    if (!panel || !detalleTitulo || !detalleTexto) {
        return;
    }

    detalleTitulo.textContent = titulo;
    detalleTexto.textContent = texto;
    panel.style.display = "block";
}
