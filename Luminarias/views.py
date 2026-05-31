from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib import messages
from django.db.models import Q, Max, Sum
from django.db.models.functions import TruncMonth
import re
from datetime import date, timedelta

from .models import Usuario, Rol, Zona, Municipio, AsignacionZona, Red, Luminaria, RegistrarLectura
from decimal import Decimal

def page_view(template_name):
    def view(request):
        return render(request, f"luminarias/{template_name}.html")

    view._name_ = template_name
    return view


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            usuario = Usuario.objects.select_related("rol").get(
                id_usuario=username,
                contrasena=password
            )
        except Usuario.DoesNotExist:
            return render(
                request,
                "luminarias/login.html",
                {"error": "Usuario o contrasena incorrectos."}
            )

        request.session["usuario_id"] = usuario.id_usuario
        request.session["usuario_nombre"] = usuario.nombre_usuario
        request.session["rol_id"] = usuario.rol_id

        if usuario.rol_id == 1:
            return redirect("dashboard_supervisor")

        if usuario.rol_id == 2:
            return redirect("dashboard_tecnico")

        return render(
            request,
            "luminarias/login.html",
            {"error": "El usuario no tiene un rol valido."}
        )

    return render(request, "luminarias/login.html")


def cambiar_contrasena(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password_actual = request.POST.get("password_actual", "")
        password_nueva = request.POST.get("password_nueva", "")
        confirmar_password = request.POST.get("confirmar_password", "")

        if password_nueva != confirmar_password:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {"error": "Las contrasenas nuevas no coinciden."}
            )

        try:
            usuario = Usuario.objects.get(
                id_usuario=username,
                contrasena=password_actual
            )
        except Usuario.DoesNotExist:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {"error": "Usuario o contrasena actual incorrectos."}
            )

        usuario.contrasena = password_nueva
        usuario.save(update_fields=["contrasena"])

        return render(
            request,
            "luminarias/login.html",
            {"success": "Contrasena actualizada correctamente. Inicia sesion."}
        )

    return render(request, "luminarias/cambiar_contrasena.html")


def cerrar_sesion(request):
    request.session.flush()
    return redirect("login")

def agregar_tecnicos(request):
    abrir_modal = None

    # Agregar \ Editar Tecnico
    if request.method == "POST":
        nombre = request.POST.get(
            "nombre_usuario",
            ""
        ).strip()

        apellido = request.POST.get(
            "apellido_usuario",
            ""
        ).strip()

        telefono = request.POST.get(
            "telefono",
            ""
        ).strip()

        contrasena = request.POST.get(
            "contrasena",
            ""
        ).strip()

        editar_id = request.POST.get(
            "editar_id"
        )

        estado = request.POST.get(
            "estado"
        )

        zona_id = request.POST.get(
            "zona"
        )

        # Validar Telefono
        if not telefono.isdigit() or len(telefono) != 8:

            messages.error(
                request,
                "El teléfono debe contener exactamente 8 dígitos"
            )

            abrir_modal = (
                "editar"
                if editar_id
                else "agregar"
            )

        # Editar Tecnico
        elif editar_id:

            tecnico = Usuario.objects.filter(
                id_usuario=editar_id,
                rol_id=2
            ).first()

            if tecnico:

                nuevo_estado = estado == "activo"

                tiene_zonas = tecnico.zonas_asignadas.exists()

                # Validar Desactivar
                if not nuevo_estado and tiene_zonas:

                    messages.error(
                        request,
                        "No se puede desactivar el técnico porque tiene zonas asignadas"
                    )

                    abrir_modal = "editar"

                else:
                    tecnico.nombre_usuario = nombre
                    tecnico.apellido_usuario = apellido
                    tecnico.telefono = telefono
                    tecnico.estado = nuevo_estado

                    # Actualizar Zona
                    tecnico.zonas_asignadas.all().delete()

                    if zona_id:

                        AsignacionZona.objects.create(
                            usuario=tecnico,
                            zona_id=zona_id
                        )

                    tecnico.save()

                    messages.success(
                        request,
                        "Técnico actualizado correctamente"
                    )

                    return redirect(
                        "agregar_tecnicos"
                    )

            else:

                messages.error(
                    request,
                    "El técnico no existe"
                )

                abrir_modal = "editar"

        # Agregar Nuevo Tecnico
        else:

            ultimo_usuario = Usuario.objects.filter(
                id_usuario__startswith="USR"
            ).aggregate(
                max_id=Max("id_usuario")
            )["max_id"]

            #Formato para seguir el id de tecnico
            if ultimo_usuario:

                numero = int(
                    re.search(
                        r"\d+",
                        ultimo_usuario
                    ).group()
                )

                nuevo_numero = numero + 1

            else:
                nuevo_numero = 1

            nuevo_codigo = f"USR{nuevo_numero:03d}"

            while Usuario.objects.filter(
                id_usuario=nuevo_codigo
            ).exists():

                nuevo_numero += 1

                nuevo_codigo = (
                    f"USR{nuevo_numero:03d}"
                )

            tecnico = Usuario.objects.create(
                id_usuario=nuevo_codigo,
                nombre_usuario=nombre,
                apellido_usuario=apellido,
                telefono=telefono,
                contrasena=contrasena,
                rol_id=2,
                estado=True
            )

            # Asignar Zonas
            if zona_id:

                AsignacionZona.objects.create(
                    usuario=tecnico,
                    zona_id=zona_id
                )

            messages.success(
                request,
                "Técnico agregado correctamente"
            )

            return redirect(
                "agregar_tecnicos"
            )

    # Filtrar Tecnicos
    q = request.GET.get(
        "q",
        ""
    ).strip()

    selected_zona = request.GET.get(
        "zona",
        ""
    ).strip()

    selected_estado = request.GET.get(
        "estado",
        ""
    ).strip()

    detalle_id = request.GET.get(
        "detalle",
        ""
    ).strip()

    rol_tecnico = Rol.objects.filter(
        roles__icontains="tecnico"
    ).first()

    if rol_tecnico:

        tecnicos = Usuario.objects.filter(
            rol_id=2
        )

    else:

        tecnicos = Usuario.objects.none()

    # Busqueda
    if q:

        tecnicos = tecnicos.filter(
            Q(id_usuario__icontains=q) |
            Q(nombre_usuario__icontains=q) |
            Q(apellido_usuario__icontains=q) |
            Q(telefono__icontains=q)
        )

    # Filtro Estado
    if selected_estado == "activo":

        tecnicos = tecnicos.filter(
            estado=True
        )

    elif selected_estado == "inactivo":

        tecnicos = tecnicos.filter(
            estado=False
        )

    # Filtro Zona
    if selected_zona:

        tecnicos = tecnicos.filter(
            zonas_asignadas__zona__id_zona=selected_zona
        )

    tecnicos = tecnicos.prefetch_related(
        "zonas_asignadas__zona__red"
    ).order_by(
        "id_usuario",
        "nombre_usuario",
        "apellido_usuario"
    )

    zonas = Zona.objects.select_related(
        "red"
    ).all().order_by(
        "nombre_zona"
    )

    # Carda
    total_tecnicos = Usuario.objects.filter(
        rol_id=2
    ).count() if rol_tecnico else 0

    tecnicos_con_zona = Usuario.objects.filter(
        rol_id=2,
        zonas_asignadas__isnull=False
    ).distinct().count() if rol_tecnico else 0

    tecnicos_sin_zona = Usuario.objects.filter(
        rol_id=2,
        zonas_asignadas__isnull=True
    ).count() if rol_tecnico else 0

    tecnicos_inactivos = Usuario.objects.filter(
        rol_id=2,
        estado=False
    ).count() if rol_tecnico else 0

    # Detalle Tecnico
    tecnico_detalle = None

    if detalle_id:

        tecnico_detalle = Usuario.objects.prefetch_related(
            "zonas_asignadas__zona__red"
        ).filter(
            id_usuario=detalle_id,
            rol_id=2
        ).first()

    context = {
        "tecnicos": tecnicos,
        "zonas": zonas,
        "q": q,
        "selected_zona": selected_zona,
        "selected_estado": selected_estado,
        "total_tecnicos": total_tecnicos,
        "tecnicos_con_zona": tecnicos_con_zona,
        "tecnicos_sin_zona": tecnicos_sin_zona,
        "tecnicos_inactivos": tecnicos_inactivos,
        "detalle_id": detalle_id,
        "tecnico_detalle": tecnico_detalle,
        "abrir_modal": abrir_modal,
    }

    return render(
        request,
        "luminarias/agregar_tecnicos.html",
        context
    )

def dashboard_supervisor(request):
    redes_consumo = []
    consumo_total_redes = 0

    for red in Red.objects.prefetch_related("luminarias", "lecturas").order_by("nombre_red"):
        ultima_lectura = red.lecturas.order_by("-fecha_lectura").first()
        total_red_luminarias = red.luminarias.count()
        fallas_red = red.luminarias.filter(estado=False).count()
        consumo_red = ultima_lectura.consumo_actual if ultima_lectura else red.consumo_esperado
        consumo_total_redes += consumo_red

        if total_red_luminarias == 0:
            estado = "Sin luminarias"
            estado_clase = "warning"
        elif fallas_red > 0:
            estado = "Con fallas"
            estado_clase = "danger"
        else:
            estado = "Activa"
            estado_clase = "success"

        redes_consumo.append({
            "nombre": red.nombre_red,
            "consumo": consumo_red,
            "estado": estado,
            "estado_clase": estado_clase,
        })

        total_tecnicos = Usuario.objects.filter(rol_id=2).count()

    context = {
        "metricas_dashboard": [
            {
                "titulo": "Total Luminarias",
                "valor": Luminaria.objects.count(),
                "clase": "",
                "unidad": "",
            },
            {
                "titulo": "Total Redes",
                "valor": Red.objects.count(),
                "clase": "success",
                "unidad": "",
            },
            {
                "titulo": "Total Técnicos",
                "valor": total_tecnicos,
                "clase": "info",
                "unidad": "",
            },
            {
                "titulo": "Consumo Total de Redes",
                "valor": consumo_total_redes,
                "clase": "",
                "unidad": "kWh",
            },
        ],
        "redes_consumo": redes_consumo,
            
    }
    return render(
        request,
        "luminarias/dashboard_supervisor.html",
        context
    )


def dashboard_tecnico(request):
    redes_consumo = []
    consumo_total_redes = 0

    for red in Red.objects.prefetch_related("luminarias", "lecturas").order_by("nombre_red"):
        ultima_lectura = red.lecturas.order_by("-fecha_lectura").first()
        total_red_luminarias = red.luminarias.count()
        fallas_red = red.luminarias.filter(estado=False).count()
        consumo_red = ultima_lectura.consumo_actual if ultima_lectura else red.consumo_esperado
        consumo_total_redes += consumo_red

        if total_red_luminarias == 0:
            estado = "Sin luminarias"
            estado_clase = "warning"
        elif fallas_red > 0:
            estado = "Con fallas"
            estado_clase = "danger"
        else:
            estado = "Activa"
            estado_clase = "success"

        redes_consumo.append({
            "nombre": red.nombre_red,
            "consumo": consumo_red,
            "estado": estado,
            "estado_clase": estado_clase,
        })

    context = {
        "metricas_dashboard": [
            {
                "titulo": "Total Luminarias",
                "valor": Luminaria.objects.count(),
                "clase": "",
                "unidad": "",
            },
            {
                "titulo": "Total Redes",
                "valor": Red.objects.count(),
                "clase": "success",
                "unidad": "",
            },
            {
                "titulo": "Total Zonas",
                "valor": Zona.objects.count(),
                "clase": "warning",
                "unidad": "",
            },
            {
                "titulo": "Consumo Total de Redes",
                "valor": consumo_total_redes,
                "clase": "",
                "unidad": "kWh",
            },
        ],
        "redes_consumo": redes_consumo,
    }

    return render(
        request,
        "luminarias/dashboard_tecnico.html",
        context
    )


def agregar_redes(request):

    # Agregar \Editar Red
    if request.method == "POST":

        nombre_red = request.POST.get(
            "nombre_red",
            ""
        ).strip()
        voltaje = request.POST.get(
            "voltaje",
            ""
        ).strip()
        zona_id = request.POST.get(
            "zona",
            ""
        ).strip()
        editar_id = request.POST.get(
            "editar_id"
        )

        # Editar Red
        if editar_id:
            red = Red.objects.filter(
                id_red=editar_id
            ).first()

            if not red:
                messages.error(
                    request,
                    "La red no existe"
                )
                return redirect("agregar_redes")

            if not nombre_red or not voltaje:
                messages.error(
                    request,
                    "Todos los campos son obligatorios"
                )
                return redirect("agregar_redes")

            red.nombre_red = nombre_red
            red.voltaje = Decimal(voltaje)
            red.save()

            messages.success(
                request,
                "Red actualizada correctamente"
            )
            return redirect("agregar_redes")

        # Agregar Nueva Red
        if not nombre_red or not voltaje or not zona_id:

            messages.error(
                request,
                "Todos los campos son obligatorios"
            )
            return redirect("agregar_redes")

        ultimo_red = Red.objects.filter(
            id_red__startswith="RED"
        ).aggregate(
            max_id=Max("id_red")
        )["max_id"]

        #Formato para seguir el id
        if ultimo_red:
            numero = int(
                re.search(r"\d+", ultimo_red).group()
            )
            nuevo_numero = numero + 1
        else:
            nuevo_numero = 1

        nuevo_codigo = f"RED{nuevo_numero:03d}"
        while Red.objects.filter(
            id_red=nuevo_codigo
        ).exists():

            nuevo_numero += 1
            nuevo_codigo = f"RED{nuevo_numero:03d}"
        try:
            zona = Zona.objects.get(
                id_zona=zona_id
            )
            if zona.red:
                messages.error(
                    request,
                    "La zona ya tiene una red asignada"
                )
                return redirect("agregar_redes")

            nueva_red = Red.objects.create(
                id_red=nuevo_codigo,
                nombre_red=nombre_red,
                voltaje=Decimal(voltaje),
                consumo_esperado=Decimal("0.00")
            )
            zona.red = nueva_red
            zona.save()

            messages.success(
                request,
                "Red agregada correctamente"
            )
        except Exception as e:

            messages.error(
                request,
                f"Error: {e}"
            )
        return redirect("agregar_redes")

    # Filtros
    q = request.GET.get(
        "q",
        ""
    ).strip()
    selected_zona = request.GET.get(
        "zona",
        ""
    ).strip()
    selected_estado = request.GET.get(
        "estado",
        ""
    ).strip()
    detalle_id = request.GET.get(
        "detalle",
        ""
    ).strip()

    porcentaje_alerta = 10
    redes_query = Red.objects.prefetch_related(
        "zonas",
        "luminarias",
        "lecturas"
    ).order_by(
        "id_red",
        "nombre_red"
    )

    # Busqued
    if q:

        redes_query = redes_query.filter(
            Q(id_red__icontains=q) |
            Q(nombre_red__icontains=q)
        )

    # Filtro Zona
    if selected_zona:

        redes_query = redes_query.filter(
            zonas__id_zona=selected_zona
        ).distinct()

    # Datos Redes
    redes_data = []
    for red in redes_query:
        ultima_lectura = red.lecturas.order_by(
            "-fecha_lectura"
        ).first()

        total_luminarias = red.luminarias.count()

        luminarias_fallando = red.luminarias.filter(
            estado=False
        ).count()

        variacion = 0

        if ultima_lectura:
            variacion = ultima_lectura.variacion_consumo
        if total_luminarias == 0:
            estado = "Sin luminarias"
            estado_clase = "warning"
        elif luminarias_fallando > 0:
            estado = "Con fallas"
            estado_clase = "inactivo"
        elif (
            ultima_lectura and
            abs(variacion) >= porcentaje_alerta
        ):
            estado = "Consumo superior al esperado"
            estado_clase = "warning"
        else:
            estado = "Activa"
            estado_clase = "activo"

        redes_data.append({
            "id_red": red.id_red,
            "nombre_red": red.nombre_red,
            "voltaje": red.voltaje,
            "consumo_esperado": red.consumo_esperado,
            "zonas": red.zonas.all(),
            "estado": estado,
            "estado_clase": estado_clase,
            "total_luminarias": total_luminarias,
            "luminarias_fallando": luminarias_fallando,
            "variacion": variacion,
        })

    # Filtro Estado
    if selected_estado == "activo":
        redes_data = [
            red for red in redes_data
            if red["estado"] == "Activa"
        ]
    elif selected_estado == "inactivo":
        redes_data = [
            red for red in redes_data
            if red["estado"] != "Activa"
        ]

    # Zonas
    zonas = Zona.objects.select_related(
        "red"
    ).all().order_by(
        "nombre_zona"
    )

    zonas_disponibles = Zona.objects.select_related(
        "red"
    ).filter(
        red__isnull=True
    ).order_by(
        "nombre_zona"
    )

    # Cards
    total_redes = Red.objects.count()

    redes_con_zona = Red.objects.filter(
        zonas__isnull=False
    ).distinct().count()
    redes_sin_zona = Red.objects.filter(
        zonas__isnull=True
    ).count()

    redes_inactivas = 0

    for red in Red.objects.prefetch_related(
        "luminarias",
        "lecturas"
    ):
        ultima_lectura = red.lecturas.order_by(
            "-fecha_lectura"
        ).first()
        total_luminarias = red.luminarias.count()
        luminarias_fallando = red.luminarias.filter(
            estado=False
        ).count()
        variacion = (
            ultima_lectura.variacion_consumo
            if ultima_lectura else 0
        )

        if (
            total_luminarias == 0 or
            luminarias_fallando > 0 or
            (
                ultima_lectura and
                abs(variacion) >= porcentaje_alerta
            )
        ):
            redes_inactivas += 1

    # Detalle Red
    red_detalle = None

    if detalle_id:
        red_detalle = next(
            (
                red for red in redes_data
                if red["id_red"] == detalle_id
            ),
            None
        )

    context = {
        "redes": redes_data,
        "zonas": zonas,
        "zonas_disponibles": zonas_disponibles,
        "q": q,
        "selected_zona": selected_zona,
        "selected_estado": selected_estado,
        "red_detalle": red_detalle,
        "detalle_id": detalle_id,
        "total_redes": total_redes,
        "redes_con_zona": redes_con_zona,
        "redes_sin_zona": redes_sin_zona,
        "redes_inactivas": redes_inactivas,
    }
    return render(
        request,
        "luminarias/agregar_redes.html",
        context
    )


PERIODOS_REPORTE = [
    {"value": "mes_actual", "label": "Mes actual"},
    {"value": "mes", "label": "Mes"},
]


#extrae los meses ingresado en la base de datos para sugerirlos en el selector del informe
def _meses_con_lecturas():
    return [
        {
            "value": mes["mes"].strftime("%Y-%m"),
            "label": mes["mes"].strftime("%m/%Y"),
        }
        for mes in RegistrarLectura.objects.annotate(
            mes=TruncMonth("fecha_lectura")
        ).values("mes").distinct().order_by("-mes")
    ]


#calcula el que quiero para el informe, mes actual o algun mes en especifico.
def _periodo_fechas(periodo, mes=None):
    hoy = timezone.localdate()
    fecha_inicio = hoy.replace(day=1)

    if periodo == "mes":
        try:
            anio, numero_mes = [int(valor) for valor in mes.split("-")]
            fecha_inicio = date(anio, numero_mes, 1)
        except (AttributeError, TypeError, ValueError):
            pass

    if fecha_inicio.month == 12:
        siguiente_mes = date(fecha_inicio.year + 1, 1, 1)
    else:
        siguiente_mes = date(fecha_inicio.year, fecha_inicio.month + 1, 1)

    return fecha_inicio, siguiente_mes - timedelta(days=1)

#convierte valores numericos  a float 
def _to_float(value):
    if value is None:
        return 0.0
    return float(value)

#Redondea valores numericos a 2 decimales para el informe
def _round(value):
    return round(_to_float(value), 2)


def _zona_nombre(red):
    if not red:
        return "Sin red"
    zonas = list(red.zonas.all())
    if not zonas:
        return "Sin zona"
    return ", ".join(zona.nombre_zona for zona in zonas)


def _estado_red(red, variacion):
    total_luminarias = red.luminarias.count()
    fallas = red.luminarias.filter(estado=False).count()

    if total_luminarias == 0:
        return "sin_luminarias"

    if fallas > 0 or abs(_to_float(variacion)) >= 10:
        return "alerta"

    return "ok"

#filtra las lecturas segun el periodo seleccionado y el municipio (si se eligio uno) para generar el informe.
def _lecturas_filtradas(fecha_inicio, fecha_fin, municipio_id):
    lecturas = RegistrarLectura.objects.select_related("red").prefetch_related(
        "red__zonas",
        "red__luminarias",
    )

    if fecha_inicio and fecha_fin:
        lecturas = lecturas.filter(
            fecha_lectura__gte=fecha_inicio,
            fecha_lectura__lte=fecha_fin
        )

    if municipio_id and municipio_id != "todos":
        lecturas = lecturas.filter(
            red__zonas__municipio_id=municipio_id
        ).distinct()

    return lecturas

#calcula consumo total, cantidad de luminarias y variacion promedio.
def _kpis_desde_rows(rows, kwh_index, lums_index, var_index=None):
   
    total_kwh = sum(_to_float(row[kwh_index]) for row in rows)
    total_lums = sum(int(_to_float(row[lums_index])) for row in rows)
    variaciones = [
        _to_float(row[var_index])
        for row in rows
        if var_index is not None and row[var_index] not in ("", None)
    ]
    variacion = sum(variaciones) / len(variaciones) if variaciones else 0

    return {
        "kwh": _round(total_kwh),
        "lums": total_lums,
        "var": _round(variacion),
        "varClass": "text-danger" if abs(variacion) >= 10 else "text-success",
    }


def _barras(rows, label_index, value_index):
    
    max_value = max([_to_float(row[value_index]) for row in rows] or [0])
    if max_value <= 0:
        return []

    return [
        {
            "label": str(row[label_index]),
            "val": _round(row[value_index]),
            "pct": min(100, _round((_to_float(row[value_index]) / max_value) * 100)),
        }
        for row in sorted(rows, key=lambda row: _to_float(row[value_index]), reverse=True)[:8]
    ]


def generar_informe(request):
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"data": _generar_reporte_data(request)})

    meses_reporte = _meses_con_lecturas()
    mes_default = (
        meses_reporte[0]["value"]
        if meses_reporte
        else timezone.localdate().strftime("%Y-%m")
    )

    municipios = [
        {"id": "todos", "nombre": "Todos los municipios"}
    ] + [
        {"id": municipio.id_municipio, "nombre": municipio.nombre_municipio}
        for municipio in Municipio.objects.order_by("nombre_municipio")
    ]

    context = {
        "periodos_reporte": PERIODOS_REPORTE,
        "periodo_default": "mes_actual",
        "mes_default": mes_default,
        "meses_reporte": meses_reporte,
        "municipios_reporte": municipios,
        "municipio_default": "todos",
    }

    return render(
        request,
        "luminarias/generar_informe.html",
        context
    )

#genera el reporte segun los filtros seleccionados, puede ser por red, luminaria, municipio o zona. 
def _generar_reporte_data(request):
   
    tipo = request.GET.get("tipo", "zona")
    periodo = request.GET.get("periodo", "mes_actual")
    mes = request.GET.get("mes", "")
    municipio_id = request.GET.get("municipio", "todos")
    fecha_inicio, fecha_fin = _periodo_fechas(periodo, mes)
    lecturas = _lecturas_filtradas(fecha_inicio, fecha_fin, municipio_id)
    red_ids_con_lecturas = list(
        lecturas.exclude(red_id__isnull=True).values_list(
            "red_id",
            flat=True
        ).distinct()
    )

    if tipo == "red":
        headers = ["Red", "Zona", "kWh", "Consumo esperado kWh", "Variacion", "Luminarias", "Estado"]
        rows = []

        redes = Red.objects.filter(
            id_red__in=red_ids_con_lecturas
        ).prefetch_related("zonas", "luminarias").order_by("nombre_red")

        if municipio_id and municipio_id != "todos":
            redes = redes.filter(zonas__municipio_id=municipio_id).distinct()

        for red in redes:
            lecturas_red = lecturas.filter(red=red)
            consumo = lecturas_red.aggregate(total=Sum("consumo_actual"))["total"] or Decimal("0")
            variacion = lecturas_red.order_by("-fecha_lectura").first()
            variacion_val = variacion.variacion_consumo if variacion else 0
            luminarias = red.luminarias.count()

            rows.append([
                red.nombre_red,
                _zona_nombre(red),
                _round(consumo),
                _round(red.consumo_esperado),
                _round(variacion_val),
                luminarias,
                _estado_red(red, variacion_val),
            ])

        totals = ["Total", "", _round(sum(row[2] for row in rows)), "", "", sum(row[5] for row in rows), ""]
        kpis = _kpis_desde_rows(rows, 2, 5, 4)
        barras = _barras(rows, 0, 2)

    elif tipo == "lum":
        headers = ["Luminaria", "Red", "Zona", "Potencia", "kWh estimado", "Estado"]
        rows = []

        luminarias = Luminaria.objects.filter(
            red_id__in=red_ids_con_lecturas
        ).select_related("red").prefetch_related(
            "red__zonas",
            "red__luminarias"
        ).order_by("id_luminaria")

        if municipio_id and municipio_id != "todos":
            luminarias = luminarias.filter(red__zonas__municipio_id=municipio_id).distinct()

        consumo_por_red = {
            item["red_id"]: item["total"] or Decimal("0")
            for item in lecturas.values("red_id").annotate(total=Sum("consumo_actual"))
        }

        potencia_por_red = {
            item["red_id"]: item["total"] or Decimal("0")
            for item in Luminaria.objects.filter(
                red_id__in=red_ids_con_lecturas
            ).values("red_id").annotate(total=Sum("potencia"))
        }

        for luminaria in luminarias:
            red = luminaria.red
            consumo_red = consumo_por_red.get(red.id_red if red else None, Decimal("0"))
            potencia_total = potencia_por_red.get(red.id_red if red else None, Decimal("0"))
            consumo_estimado = Decimal("0")

            if potencia_total:
                consumo_estimado = consumo_red * luminaria.potencia / potencia_total

            rows.append([
                luminaria.id_luminaria,
                red.nombre_red if red else "Sin red",
                _zona_nombre(red),
                _round(luminaria.potencia),
                _round(consumo_estimado),
                "Activa" if luminaria.estado else "Con falla",
            ])

        totals = ["Total", "", "", _round(sum(row[3] for row in rows)), _round(sum(row[4] for row in rows)), ""]
        kpis = {"kwh": totals[4], "lums": len(rows), "var": 0, "varClass": ""}
        barras = _barras(rows, 0, 4)

    elif tipo == "mun":
        headers = ["Municipio", "Zonas", "Redes", "Luminarias", "kWh", "Variacion"]
        rows = []
        municipios = Municipio.objects.filter(
            zonas__red_id__in=red_ids_con_lecturas
        ).prefetch_related("zonas__red").distinct().order_by("nombre_municipio")

        if municipio_id and municipio_id != "todos":
            municipios = municipios.filter(id_municipio=municipio_id)

        for municipio in municipios:
            zonas = [
                zona
                for zona in municipio.zonas.all()
                if zona.red_id in red_ids_con_lecturas
            ]
            red_ids = {zona.red_id for zona in zonas}
            lecturas_mun = lecturas.filter(red_id__in=red_ids)
            consumo = lecturas_mun.aggregate(total=Sum("consumo_actual"))["total"] or Decimal("0")
            ultima = lecturas_mun.order_by("-fecha_lectura").first()
            luminarias = Luminaria.objects.filter(red_id__in=red_ids).count()

            rows.append([
                municipio.nombre_municipio,
                len(zonas),
                len(red_ids),
                luminarias,
                _round(consumo),
                _round(ultima.variacion_consumo if ultima else 0),
            ])

        totals = ["Total", sum(row[1] for row in rows), sum(row[2] for row in rows), sum(row[3] for row in rows), _round(sum(row[4] for row in rows)), ""]
        kpis = _kpis_desde_rows(rows, 4, 3, 5)
        barras = _barras(rows, 0, 4)

    else:
        headers = ["Zona", "Municipio", "Red", "kWh", "Luminarias", "Variacion"]
        rows = []
        zonas = Zona.objects.filter(
            red_id__in=red_ids_con_lecturas
        ).select_related("municipio", "red").prefetch_related(
            "red__luminarias"
        ).order_by("nombre_zona")

        if municipio_id and municipio_id != "todos":
            zonas = zonas.filter(municipio_id=municipio_id)

        for zona in zonas:
            lecturas_zona = lecturas.filter(red=zona.red) if zona.red else RegistrarLectura.objects.none()
            consumo = lecturas_zona.aggregate(total=Sum("consumo_actual"))["total"] or Decimal("0")
            ultima = lecturas_zona.order_by("-fecha_lectura").first()
            luminarias = zona.red.luminarias.count() if zona.red else 0

            rows.append([
                zona.nombre_zona,
                zona.municipio.nombre_municipio if zona.municipio else "Sin municipio",
                zona.red.nombre_red if zona.red else "Sin red",
                _round(consumo),
                luminarias,
                _round(ultima.variacion_consumo if ultima else 0),
            ])

        totals = ["Total", "", "", _round(sum(row[3] for row in rows)), sum(row[4] for row in rows), ""]
        kpis = _kpis_desde_rows(rows, 3, 4, 5)
        barras = _barras(rows, 0, 3)

    return {
        "headers": headers,
        "rows": rows,
        "totals": totals,
        "kpis": kpis,
        "barras": barras,
    }


registrar_lecturas = page_view("registrar_lecturas")
agregar_zonas = page_view("agregar_zonas")
agregar_luminarias = page_view("agregar_luminarias")
base = page_view("base")
base_supervisor = page_view("base_supervisor")
base_tecnicos = page_view("base_tecnicos")
