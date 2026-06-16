const TIPO_LABEL = {
zona: "Por zona",
red: "Por red",
lum: "Por luminaria",
mun: "Por municipio",
};

const ESTADOS_RED = {
ok: { label: "Normal", className: "badge-activo" },
alerta: { label: "Alerta", className: "badge-warning" },
sin_luminarias: { label: "Sin luminarias", className: "badge-inactivo" },
};

let reporteActivo = false;

function getSelectedOptionText(id) {
const select = document.getElementById(id);
return select.options[select.selectedIndex]?.textContent.trim() || "";
}

function decimal(value) {
const numberValue = Number(value || 0);
return Number.isFinite(numberValue) ? numberValue : 0;
}

function formatNumber(value, decimals = 2) {
return decimal(value).toLocaleString("es-SV", {
minimumFractionDigits: decimals,
maximumFractionDigits: decimals,
});
}

function formatInteger(value) {
return decimal(value).toLocaleString("es-SV", {
maximumFractionDigits: 0,
});
}

function formatPercent(value) {
const numberValue = decimal(value);
const sign = numberValue > 0 ? "+" : "";
return sign + formatNumber(numberValue, 2) + "%";
}

function formatCell(value, header) {
if (value === "" || value === null || value === undefined) {
return "";
}

const normalizedHeader = header.toLowerCase();

if (normalizedHeader.includes("kwh")) {
return formatNumber(value, 2);
}

if (normalizedHeader.includes("potencia")) {
return formatNumber(value, 2) + " W";
}

if (normalizedHeader.includes("variacion")) {
return formatPercent(value);
}

if (
normalizedHeader.includes("luminarias") ||
normalizedHeader.includes("horas") ||
normalizedHeader.includes("zonas") ||
normalizedHeader.includes("redes")
) {
return formatInteger(value);
}

return value ?? "";
}

function mostrar(id) {
["estado-vacio", "estado-cargando", "estado-resultado"].forEach((sec) => {
document.getElementById(sec).classList.toggle("hidden", sec !== id);
});
}

function limpiarTabla() {
document.getElementById("rep-thead").innerHTML = "";
document.getElementById("rep-tbody").innerHTML = "";
document.getElementById("rep-tfoot").innerHTML = "";
}

function setExportEnabled(enabled) {
document.getElementById("btn-pdf").disabled = !enabled;
}

function getReportParams() {
return new URLSearchParams({
tipo: document.getElementById("rep-tipo").value,
periodo: document.getElementById("rep-periodo").value,
mes: document.getElementById("rep-mes").value,
municipio: document.getElementById("rep-municipio").value,
});
}

function actualizarCampoMes() {
const periodo = document.getElementById("rep-periodo").value;
document.getElementById("rep-mes-group").classList.toggle("hidden", periodo !== "mes");
}

function getReportUrl() {
return document.querySelector(".report-panel").dataset.reportUrl;
}

async function cargarDatosReporte() {
const params = getReportParams();
const response = await fetch(`${getReportUrl()}?${params.toString()}`, {
headers: {
"X-Requested-With": "XMLHttpRequest",
},
});

if (!response.ok) {
throw new Error("No se pudo generar el reporte.");
}

const payload = await response.json();
return payload.data;
}

function cargarKpis(datos) {
document.getElementById("kpi-kwh").textContent = formatNumber(datos.kpis.kwh, 2);
document.getElementById("kpi-lums").textContent = formatInteger(datos.kpis.lums);

const variacion = document.getElementById("kpi-var");
variacion.textContent = formatPercent(datos.kpis.var);
variacion.className = datos.kpis.varClass || "";
}

function cargarBarras(datos) {
const seccion = document.getElementById("sec-barras");
const contenedor = document.getElementById("barras-cont");

if (!datos.barras || datos.barras.length === 0) {
seccion.hidden = true;
contenedor.innerHTML = "";
return;
}

seccion.hidden = false;
contenedor.innerHTML = "";

datos.barras.forEach((barra) => {
const row = document.createElement("div");
row.className = "bar-row";

const label = document.createElement("span");
label.className = "bar-lbl";
label.textContent = barra.label;

const track = document.createElement("div");
track.className = "bar-track";

const fill = document.createElement("div");
fill.className = "bar-fill";
fill.style.width = "0%";
fill.dataset.pct = barra.pct;

const value = document.createElement("span");
value.className = "bar-val";
value.textContent = formatNumber(barra.val, 2);

track.appendChild(fill);
row.append(label, track, value);
contenedor.appendChild(row);
});

requestAnimationFrame(() => {
contenedor.querySelectorAll(".bar-fill").forEach((bar) => {
bar.style.width = bar.dataset.pct + "%";
});
});
}

function cargarTabla(tipo, datos) {
limpiarTabla();

const thead = document.getElementById("rep-thead");
const tbody = document.getElementById("rep-tbody");
const tfoot = document.getElementById("rep-tfoot");

const headerRow = document.createElement("tr");
datos.headers.forEach((header) => {
const th = document.createElement("th");
th.textContent = header;
headerRow.appendChild(th);
});
thead.appendChild(headerRow);

if (!datos.rows.length) {
const tr = document.createElement("tr");
const td = document.createElement("td");
td.className = "empty-state";
td.colSpan = datos.headers.length;
td.textContent = "No hay datos registrados para estos parametros";
tr.appendChild(td);
tbody.appendChild(tr);
} else {
datos.rows.forEach((row) => {
const tr = document.createElement("tr");

datos.headers.forEach((header, index) => {
const td = document.createElement("td");
const value = row[index];

if (tipo === "red" && index === datos.headers.length - 1) {
const estado = ESTADOS_RED[value] || ESTADOS_RED.alerta;
const badge = document.createElement("span");
badge.className = "badge " + estado.className;
badge.textContent = estado.label;
td.appendChild(badge);
} else {
td.textContent = formatCell(value, header);
}

tr.appendChild(td);
});

tbody.appendChild(tr);
});
}

const totalRow = document.createElement("tr");
datos.totals.forEach((value, index) => {
const td = document.createElement("td");
td.textContent = formatCell(value, datos.headers[index] || "");
totalRow.appendChild(td);
});
tfoot.appendChild(totalRow);
}

async function generarReporte() {
const tipo = document.getElementById("rep-tipo").value;

mostrar("estado-cargando");
setExportEnabled(false);

try {
const datos = await cargarDatosReporte();

document.getElementById("res-titulo").textContent =
"Reporte de consumo - " + TIPO_LABEL[tipo];
document.getElementById("res-sub").textContent =
(document.getElementById("rep-periodo").value === "mes"
? "Mes " + document.getElementById("rep-mes").value
: getSelectedOptionText("rep-periodo")) + " | " + getSelectedOptionText("rep-municipio");

cargarKpis(datos);
cargarBarras(datos);
cargarTabla(tipo, datos);

document.getElementById("footer-fecha").textContent =
new Date().toLocaleDateString("es-SV");
document.getElementById("footer-municipio").textContent =
getSelectedOptionText("rep-municipio");

reporteActivo = true;
setExportEnabled(true);
mostrar("estado-resultado");
} catch (error) {
reporteActivo = false;
limpiarTabla();
mostrar("estado-vacio");
console.error(error);
}
}

function exportarPDF() {
if (!reporteActivo) {
return;
}

const ventana = window.open("", "_blank");
const tabla = document.getElementById("rep-tabla").outerHTML;
const titulo = document.getElementById("res-titulo").textContent;
const subtitulo = document.getElementById("res-sub").textContent;

ventana.document.write(`
<html>
<head>
<title>${titulo}</title>
<style>
body{font-family:Arial,sans-serif;padding:28px;color:#1e293b}
h1{font-size:22px;margin:0 0 6px}
p{color:#64748b;margin:0 0 20px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{border:1px solid #dbe3ec;padding:8px;text-align:left}
th{background:#1e3a5f;color:#fff}
tfoot td{font-weight:bold;background:#f4f7fb}
</style>
</head>
<body>
<h1>${titulo}</h1>
<p>${subtitulo}</p>
${tabla}
<script>window.print();<\/script>
</body>
</html>
`);

ventana.document.close();
}

document.addEventListener("DOMContentLoaded", () => {
document.getElementById("btn-generar").addEventListener("click", generarReporte);
document.getElementById("btn-pdf").addEventListener("click", exportarPDF);
actualizarCampoMes();

["rep-tipo", "rep-periodo", "rep-mes", "rep-municipio"].forEach((id) => {
document.getElementById(id).addEventListener("change", () => {
actualizarCampoMes();
reporteActivo = false;
setExportEnabled(false);
mostrar("estado-vacio");
});
});
});

window.generarReporte = generarReporte;
window.exportarPDF = exportarPDF;
