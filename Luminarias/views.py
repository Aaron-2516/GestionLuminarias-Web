from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q, Max, Sum, Count
from django.db.models.functions import TruncMonth
import re
from datetime import date, timedelta

from .models import Usuario, Rol, Zona, Municipio, AsignacionZona, Red, Luminaria, RegistrarLectura, Crea
from decimal import Decimal

def page_view(template_name):
    def view(request):
        return render(request, f"luminarias/{template_name}.html")

    view._name_ = template_name
    return view


def _siguiente_codigo(modelo, prefijo, campo_id):
    ultimo_codigo = modelo.objects.filter(
        **{f"{campo_id}__startswith": prefijo}
    ).aggregate(
        max_id=Max(campo_id)
    )["max_id"]

    if ultimo_codigo:
        coincidencia = re.search(r"\d+", ultimo_codigo)
        numero = int(coincidencia.group()) if coincidencia else 0
        siguiente_numero = numero + 1
    else:
        siguiente_numero = 1

    codigo = f"{prefijo}{siguiente_numero:03d}"

    while modelo.objects.filter(**{campo_id: codigo}).exists():
        siguiente_numero += 1
        codigo = f"{prefijo}{siguiente_numero:03d}"

    return codigo


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
        request.session["usuario_nombre"] = f"{usuario.nombre_usuario} {usuario.apellido_usuario}"
        request.session["rol_id"] = usuario.rol_id
        request.session["contrasena_temporal"] = password

        if usuario.rol_id == 1:
            return redirect("dashboard_supervisor")

        if usuario.rol_id == 2:
            # Detectar si es primer acceso para técnico
            if usuario.primer_acceso:
                return redirect("cambiar_contrasena_primer_acceso")
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

        messages.success(request, "Contraseña actualizada correctamente. Inicia sesión.")
        return redirect("login")

    return render(request, "luminarias/cambiar_contrasena.html")


def cambiar_contrasena_primer_acceso(request):
    """Vista especial para cambiar contraseña en primer acceso de técnicos"""
    usuario_id = request.session.get("usuario_id")
    contrasena_temporal = request.session.get("contrasena_temporal")

    # Validar que esté autenticado y sea técnico
    if not usuario_id or request.session.get("rol_id") != 2:
        return redirect("login")

    if request.method == "POST":
        password_nueva = request.POST.get("password_nueva", "").strip()
        confirmar_password = request.POST.get("confirmar_password", "").strip()

        if not password_nueva or not confirmar_password:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {
                    "error": "Los campos de contraseña no pueden estar vacíos.",
                    "primer_acceso": True,
                    "usuario_id": usuario_id,
                    "usuario_nombre": request.session.get("usuario_nombre")
                }
            )

        if password_nueva != confirmar_password:
            return render(
                request,
                "luminarias/cambiar_contrasena.html",
                {
                    "error": "Las contraseñas nuevas no coinciden.",
                    "primer_acceso": True,
                    "usuario_id": usuario_id,
                    "usuario_nombre": request.session.get("usuario_nombre")
                }
            )

        try:
            usuario = Usuario.objects.get(id_usuario=usuario_id)
            usuario.contrasena = password_nueva
            usuario.primer_acceso = False
            usuario.save(update_fields=["contrasena", "primer_acceso"])

            messages.success(request, "Contraseña establecida correctamente.")
            return redirect("dashboard_tecnico")

        except Usuario.DoesNotExist:
            return redirect("login")

    context = {
        "primer_acceso": True,
        "usuario_id": usuario_id,
        "usuario_nombre": request.session.get("usuario_nombre")
    }

    return render(
        request,
        "luminarias/cambiar_contrasena.html",
        context
    )


def cerrar_sesion(request):
    request.session.flush()
    return redirect("login")


def agregar_tecnicos(request):
    abrir_modal = None

    # Agregar / Editar Tecnico / Eliminar Tecnico
    if request.method == "POST":
        nombre = request.POST.get("nombre_usuario", "").strip()
        apellido = request.POST.get("apellido_usuario", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        contrasena = request.POST.get("contrasena", "").strip()
        editar_id = request.POST.get("editar_id", "").strip()
        eliminar_id = request.POST.get("eliminar_id", "").strip()
        estado = request.POST.get("estado", "").strip()

        zona_ids = []
        if editar_id:
            zona_ids = request.POST.getlist("zona_editar")
        # else:
        #     zona_ids = request.POST.getlist(
        #         "zona_agregar"
        #     )

        # Eliminar Tecnico
        if eliminar_id:
            tecnico = Usuario.objects.filter(
                id_usuario=eliminar_id,
                rol_id=2
            ).first()

            if not tecnico:
                messages.error(
                    request,
                    "El técnico no existe"
                )
            elif tecnico.zonas_asignadas.exists():
                messages.error(
                    request,
                    f"No se puede eliminar el técnico {tecnico.nombre_usuario} {tecnico.apellido_usuario} porque tiene zonas asignadas"
                )
            else:
                try:
                    tecnico.delete()
                    messages.success(
                        request,
                        f"Técnico eliminado {tecnico.nombre_usuario} {tecnico.apellido_usuario} correctamente"
                    )
                except IntegrityError:
                    messages.error(
                        request,
                        f"No se puede eliminar el técnico {tecnico.nombre_usuario} {tecnico.apellido_usuario} porque tiene dependencias registradas"
                    )

            return redirect(
                "agregar_tecnicos"
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

                    for zona_id in zona_ids:
                        AsignacionZona.objects.create(
                            usuario=tecnico,
                            zona_id=zona_id
                        )

                    tecnico.save()
                    messages.success(
                        request,
                        f"Técnico {tecnico.nombre_usuario} {tecnico.apellido_usuario} actualizado correctamente"
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

        # Agregar Nuevo Tecnico FORMATO ID USR001, USR002, etc
        else:
            nuevo_codigo = _siguiente_codigo(
                Usuario,
                "USR",
                "id_usuario"
            )

            tecnico = Usuario.objects.create(
                id_usuario=nuevo_codigo,
                nombre_usuario=nombre,
                apellido_usuario=apellido,
                telefono=telefono,
                contrasena=contrasena,
                rol_id=2,
                estado=True,
                primer_acceso=True
            )

            # Asignar Zonas
            if zona_ids:
                for zona_id in zona_ids:
                    AsignacionZona.objects.create(
                        usuario=tecnico,
                        zona_id=zona_id
                    )

            messages.success(
                request,
                f"Técnico {tecnico.nombre_usuario} {tecnico.apellido_usuario} agregado correctamente"
            )

            return redirect(
                "agregar_tecnicos"
            )

    # Obtener tecnicos en tabla
    q = request.GET.get("q", "").strip()
    selected_zona = request.GET.get("zona", "").strip()
    selected_estado = request.GET.get("estado", "").strip()
    detalle_id = request.GET.get("detalle", "").strip()
    rol_tecnico = Rol.objects.filter(roles__icontains="tecnico").first()

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

    # Cards
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
    zonas_estado = []

    consumo_total_redes = 0
    total_tecnicos = Usuario.objects.filter(
        rol_id=2
    ).count()
    # =========================
    # CONSUMO POR RED
    # =========================

    redes = Red.objects.prefetch_related(
        "luminarias",
        "lecturas"
    ).order_by(
        "id_red"
    )

    for red in redes:
        ultima_lectura = red.lecturas.order_by(
            "-fecha_lectura"
        ).first()

        total_red_luminarias = red.luminarias.count()

        fallas_red = red.luminarias.filter(
            estado=False
        ).count()

        consumo_red = (
            ultima_lectura.consumo_actual
            if ultima_lectura
            else red.consumo_esperado
        )

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

    # =========================
    # ESTADO POR ZONA
    # =========================

    zonas = Zona.objects.all().order_by(
        "id_zona",
    )

    for zona in zonas:
        redes_zona = Red.objects.filter(
            zonas=zona
        ).prefetch_related(
            "luminarias"
        )

        total_redes_zona = redes_zona.count()
        total_luminarias_zona = 0
        fallas_zona = 0

        for red in redes_zona:
            total_luminarias_zona += red.luminarias.count()

            fallas_zona += red.luminarias.filter(
                estado=False
            ).count()

        if total_redes_zona == 0:
            estado = "Sin redes"
            estado_clase = "warning"

        elif total_luminarias_zona == 0:
            estado = "Sin luminarias"
            estado_clase = "warning"

        elif fallas_zona > 0:
            estado = "Con fallas"
            estado_clase = "danger"

        else:
            estado = "Activa"
            estado_clase = "success"

        zonas_estado.append({
            "nombre": zona.nombre_zona,
            "luminarias": total_luminarias_zona,
            "estado": estado,
            "estado_clase": estado_clase,
        })

    context = {
        "metricas_dashboard": [
            {
                "titulo": "Total Técnicos",
                "valor": total_tecnicos,
                "clase": "",
                "unidad": "",
            },
            {
                "titulo": "Total Zonas",
                "valor": Zona.objects.count(),
                "clase": "",
                "unidad": "",
            },
            {
                "titulo": "Total Redes",
                "valor": Red.objects.count(),
                "clase": "",
                "unidad": "",
            },
            {
                "titulo": "Total Luminarias",
                "valor": Luminaria.objects.count(),
                "clase": "",
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
        "zonas_estado": zonas_estado,
    }

    return render(
        request,
        "luminarias/dashboard_supervisor.html",
        context
    )


def dashboard_tecnico(request):
    redes_consumo = []
    consumo_total_redes = 0
    usuario_id = request.session.get("usuario_id")
    redes_asignadas = Red.objects.none()

    if usuario_id:
        redes_asignadas = Red.objects.prefetch_related("luminarias", "lecturas").filter(
            zonas__tecnicos_asignados__usuario_id=usuario_id
        ).distinct().order_by("nombre_red")

    for red in redes_asignadas:
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

    zonas_asignadas = Zona.objects.filter(
        tecnicos_asignados__usuario_id=usuario_id
    ).order_by("nombre_zona").distinct() if usuario_id else Zona.objects.none()
    zonas_asignadas_count = zonas_asignadas.count()

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
                "titulo": "Zonas Asignadas",
                "valor": zonas_asignadas_count,
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
        "zonas_asignadas": zonas_asignadas,
    }

    return render(
        request,
        "luminarias/dashboard_tecnico.html",
        context
    )


def agregar_redes(request):
    # Agregar / Editar Red / Eliminar Red
    if request.method == "POST":
        nombre_red = request.POST.get("nombre_red", "").strip()
        voltaje = request.POST.get("voltaje", "").strip()
        # zona_id = request.POST.get("zona", "").strip()
        editar_id = request.POST.get("editar_id", "").strip()
        eliminar_id = request.POST.get("eliminar_id", "").strip()

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
                f"Red {red.nombre_red} actualizada correctamente"
            )
            return redirect("agregar_redes")
# Eliminar Red
        if eliminar_id:
            red = Red.objects.filter(
                id_red=eliminar_id
            ).first()

            if not red:
                messages.error(
                    request,
                    "La red no existe"
                )
            elif red.zonas.exists() or red.luminarias.exists() or red.lecturas.exists():
                messages.error(
                    request,
                    "No se puede eliminar la red porque tiene relaciones asociadas"
                )
            else:
                try:
                    red.delete()
                    messages.success(
                        request,
                        f"Red {red.nombre_red} eliminada correctamente"
                    )
                except IntegrityError:
                    messages.error(
                        request,
                        f"No se puede eliminar la red {red.nombre_red} porque tiene dependencias registradas"
                    )

            return redirect("agregar_redes")

        ###### Agregar Nueva Red
        # if not nombre_red or not voltaje or not zona_id:

        #     messages.error(
        #         request,
        #         "Todos los campos son obligatorios"
        #     )
        #     return redirect("agregar_redes")
        
        # Agregar Nueva Red FORMATO ID RED001, RED002, etc
        nuevo_codigo = _siguiente_codigo(
            Red,
            "RED",
            "id_red"
        )
        try:
            # zona = Zona.objects.get(
            #     id_zona=zona_id
            # )
            usuario_actual = Usuario.objects.filter(
                id_usuario=request.session.get("usuario_id")
            ).first()
            # if zona.red:
            #     messages.error(
            #         request,
            #         "La zona ya tiene una red asignada"
            #     )
            #     return redirect("agregar_redes")

            nueva_red = Red.objects.create(
                id_red=nuevo_codigo,
                nombre_red=nombre_red,
                voltaje=Decimal(voltaje),
                consumo_esperado=Decimal("0.00"),
            )

            # zona.red = nueva_red
            # zona.save()

            messages.success(
                request,
                f"Red {nueva_red.nombre_red} agregada correctamente"
            )
        except Exception as e:
            messages.error(
                request,
                f"Error: {e}"
            )

        return redirect("agregar_redes")

   # Filtros
    q = request.GET.get("q", "").strip()
    selected_zona = request.GET.get("zona", "").strip()
    selected_estado = request.GET.get("estado", "").strip()
    detalle_id = request.GET.get("detalle", "").strip()
    usuario_actual_id = request.session.get("usuario_id")

    porcentaje_alerta = 10
    redes_query = Red.objects.prefetch_related(
        "zonas",
        "luminarias",
        "lecturas"
    ).order_by(
        "id_red",
        "nombre_red"
    )

    # Busqueda
    if q:
        redes_usuario_query = redes_usuario_query.filter(
            Q(id_red__icontains=q) |
            Q(nombre_red__icontains=q)
        )

    # Filtro Zona
    if selected_zona:
        redes_usuario_query = redes_usuario_query.filter(
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

    # Cargar Zonas para Filtro y Modal
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


def agregar_zonas(request):
    if request.method == "POST":
        nombre_zona = request.POST.get("nombre_zona", "").strip()
        tipo_zona = request.POST.get("tipo_zona", "").strip()
        red_id = request.POST.get("red", "").strip()
        municipio_id = request.POST.get("municipio", "").strip()
        editar_id = request.POST.get("editar_id", "").strip()
        eliminar_id = request.POST.get("eliminar_id", "").strip()

        if eliminar_id:
            zona = Zona.objects.filter(id_zona=eliminar_id).select_related("red").first()

            if not zona:
                messages.error(request, "La zona no existe")
            elif zona.red_id or zona.tecnicos_asignados.exists():
                messages.error(
                    request,
                    "No se puede eliminar la zona porque tiene relaciones asociadas"
                )
            else:
                try:
                    zona.delete()
                    messages.success(request, "Zona eliminada correctamente")
                except IntegrityError:
                    messages.error(
                        request,
                        "No se puede eliminar la zona porque tiene dependencias registradas"
                    )

            return redirect("agregar_zonas")

        if not nombre_zona or not tipo_zona:
            messages.error(request, "El nombre y el tipo de la zona son obligatorios")
            return redirect("agregar_zonas")

        red = None
        if red_id:
            red = Red.objects.filter(id_red=red_id).first()
            if not red:
                messages.error(request, "La red seleccionada no existe")
                return redirect("agregar_zonas")

        municipio = None
        if municipio_id:
            municipio = Municipio.objects.filter(id_municipio=municipio_id).first()
            if not municipio:
                messages.error(request, "El municipio seleccionado no existe")
                return redirect("agregar_zonas")

        if editar_id:
            zona = Zona.objects.filter(id_zona=editar_id).first()

            if not zona:
                messages.error(request, "La zona no existe")
                return redirect("agregar_zonas")

            zona.nombre_zona = nombre_zona
            zona.tipo_zona = tipo_zona
            zona.red = red
            zona.municipio = municipio
            zona.save()

            messages.success(request, "Zona actualizada correctamente")
            return redirect("agregar_zonas")

        nueva_zona = Zona.objects.create(
            id_zona=_siguiente_codigo(Zona, "ZON", "id_zona"),
            nombre_zona=nombre_zona,
            tipo_zona=tipo_zona,
            red=red,
            municipio=municipio,
        )

        messages.success(request, f"Zona {nueva_zona.nombre_zona} agregada correctamente")
        return redirect("agregar_zonas")

    q = request.GET.get("q", "").strip()
    selected_tipo = request.GET.get("tipo", "").strip()
    selected_red = request.GET.get("red", "").strip()
    selected_municipio = request.GET.get("municipio", "").strip()
    detalle_id = request.GET.get("detalle", "").strip()

    zonas_query = Zona.objects.select_related(
        "red",
        "municipio",
    ).prefetch_related(
        "tecnicos_asignados__usuario",
        "red__luminarias",
    ).order_by(
        "id_zona",
        "nombre_zona"
    )

    if q:
        zonas_query = zonas_query.filter(
            Q(id_zona__icontains=q) |
            Q(nombre_zona__icontains=q) |
            Q(tipo_zona__icontains=q) |
            Q(red__nombre_red__icontains=q) |
            Q(municipio__nombre_municipio__icontains=q)
        )

    if selected_tipo:
        zonas_query = zonas_query.filter(tipo_zona__icontains=selected_tipo)

    if selected_red:
        zonas_query = zonas_query.filter(red_id=selected_red)

    if selected_municipio:
        zonas_query = zonas_query.filter(municipio_id=selected_municipio)

    zonas_data = []
    for zona in zonas_query:
        luminarias_totales = zona.red.luminarias.count() if zona.red_id else 0
        luminarias_activas = zona.red.luminarias.filter(estado=True).count() if zona.red_id else 0
        luminarias_inactivas = zona.red.luminarias.filter(estado=False).count() if zona.red_id else 0

        if not zona.red_id:
            estado = "Sin red"
            estado_clase = "warning"
        elif luminarias_activas > 0 and luminarias_inactivas == 0:
            estado = "Activa"
            estado_clase = "activo"
        elif luminarias_activas > 0:
            estado = "Con observaciones"
            estado_clase = "warning"
        else:
            estado = "En mantenimiento"
            estado_clase = "inactivo"

        tecnicos = [
            f"{asignacion.usuario.nombre_usuario} {asignacion.usuario.apellido_usuario}"
            for asignacion in zona.tecnicos_asignados.all()
            if asignacion.usuario
        ]

        zonas_data.append({
            "id_zona": zona.id_zona,
            "nombre_zona": zona.nombre_zona,
            "tipo_zona": zona.tipo_zona,
            "red": zona.red,
            "municipio": zona.municipio,
            "estado": estado,
            "estado_clase": estado_clase,
            "luminarias_totales": luminarias_totales,
            "luminarias_activas": luminarias_activas,
            "luminarias_inactivas": luminarias_inactivas,
            "tecnicos": tecnicos,
        })

    total_zonas = len(zonas_data)
    zonas_con_luminarias_activas = sum(1 for zona in zonas_data if zona["luminarias_activas"] > 0)
    zonas_sin_luminarias_activas = total_zonas - zonas_con_luminarias_activas
    zonas_en_mantenimiento = sum(1 for zona in zonas_data if zona["estado_clase"] != "activo")

    zona_detalle = None
    if detalle_id:
        zona_detalle = next(
            (zona for zona in zonas_data if zona["id_zona"] == detalle_id),
            None
        )

    context = {
        "zonas": zonas_data,
        "redes": Red.objects.order_by("nombre_red"),
        "municipios": Municipio.objects.order_by("nombre_municipio"),
        "tipos_zona": Zona.objects.order_by("tipo_zona").values_list("tipo_zona", flat=True).distinct(),
        "q": q,
        "selected_tipo": selected_tipo,
        "selected_red": selected_red,
        "selected_municipio": selected_municipio,
        "total_zonas": total_zonas,
        "zonas_con_luminarias_activas": zonas_con_luminarias_activas,
        "zonas_sin_luminarias_activas": zonas_sin_luminarias_activas,
        "zonas_en_mantenimiento": zonas_en_mantenimiento,
        "zona_detalle": zona_detalle,
        "detalle_id": detalle_id,
    }

    return render(request, "luminarias/agregar_zonas.html", context)


def agregar_luminarias(request):
    if request.method == "POST":
        potencia = request.POST.get("potencia", "").strip()
        estado = request.POST.get("estado", "").strip()
        tipo = request.POST.get("tipo", "").strip()
        red_id = request.POST.get("red", "").strip()
        fecha_instalacion = request.POST.get("fecha_instalacion", "").strip()
        editar_id = request.POST.get("editar_id", "").strip()
        eliminar_id = request.POST.get("eliminar_id", "").strip()

        if eliminar_id:
            luminaria = Luminaria.objects.filter(id_luminaria=eliminar_id).first()

            if not luminaria:
                messages.error(request, "La luminaria no existe")
            else:
                luminaria.delete()
                messages.success(request, "Luminaria eliminada correctamente")

            return redirect("agregar_luminarias")

        if not potencia or not estado or not tipo or not red_id or not fecha_instalacion:
            messages.error(request, "Todos los campos son obligatorios")
            return redirect("agregar_luminarias")

        red = Red.objects.filter(id_red=red_id).first()
        if not red:
            messages.error(request, "La red seleccionada no existe")
            return redirect("agregar_luminarias")

        estado_bool = estado == "activo"

        if editar_id:
            luminaria = Luminaria.objects.filter(id_luminaria=editar_id).first()

            if not luminaria:
                messages.error(request, "La luminaria no existe")
                return redirect("agregar_luminarias")

            luminaria.potencia = Decimal(potencia)
            luminaria.estado = estado_bool
            luminaria.tipo = tipo
            luminaria.red = red
            luminaria.fecha_instalacion = fecha_instalacion
            luminaria.save()

            messages.success(request, "Luminaria actualizada correctamente")
            return redirect("agregar_luminarias")

        luminaria = Luminaria.objects.create(
            id_luminaria=_siguiente_codigo(Luminaria, "LUM", "id_luminaria"),
            potencia=Decimal(potencia),
            estado=estado_bool,
            tipo=tipo,
            red=red,
            fecha_instalacion=fecha_instalacion,
        )

        messages.success(request, f"Luminaria {luminaria.id_luminaria} agregada correctamente")
        return redirect("agregar_luminarias")

    q = request.GET.get("q", "").strip()
    selected_red = request.GET.get("red", "").strip()
    selected_estado = request.GET.get("estado", "").strip()
    selected_tipo = request.GET.get("tipo", "").strip()
    detalle_id = request.GET.get("detalle", "").strip()

    luminarias_query = Luminaria.objects.select_related("red").order_by("id_luminaria")

    if q:
        luminarias_query = luminarias_query.filter(
            Q(id_luminaria__icontains=q) |
            Q(tipo__icontains=q) |
            Q(red__nombre_red__icontains=q) |
            Q(potencia__icontains=q)
        )

    if selected_red:
        luminarias_query = luminarias_query.filter(red_id=selected_red)

    if selected_tipo:
        luminarias_query = luminarias_query.filter(tipo__icontains=selected_tipo)

    if selected_estado == "activo":
        luminarias_query = luminarias_query.filter(estado=True)
    elif selected_estado == "inactivo":
        luminarias_query = luminarias_query.filter(estado=False)

    luminarias_data = []
    for luminaria in luminarias_query:
        estado_texto = "Activa" if luminaria.estado else "Inactiva"
        estado_clase = "activo" if luminaria.estado else "inactivo"

        luminarias_data.append({
            "id_luminaria": luminaria.id_luminaria,
            "potencia": luminaria.potencia,
            "estado": luminaria.estado,
            "estado_texto": estado_texto,
            "estado_clase": estado_clase,
            "tipo": luminaria.tipo,
            "red": luminaria.red,
            "fecha_instalacion": luminaria.fecha_instalacion,
        })

    total_luminarias = len(luminarias_data)
    luminarias_activas = sum(1 for luminaria in luminarias_data if luminaria["estado"])
    luminarias_inactivas = total_luminarias - luminarias_activas
    luminarias_sin_red = sum(1 for luminaria in luminarias_data if luminaria["red"] is None)

    luminaria_detalle = None
    if detalle_id:
        luminaria_detalle = next(
            (luminaria for luminaria in luminarias_data if luminaria["id_luminaria"] == detalle_id),
            None
        )

    context = {
        "luminarias": luminarias_data,
        "redes": Red.objects.order_by("nombre_red"),
        "q": q,
        "selected_red": selected_red,
        "selected_estado": selected_estado,
        "selected_tipo": selected_tipo,
        "total_luminarias": total_luminarias,
        "luminarias_activas": luminarias_activas,
        "luminarias_inactivas": luminarias_inactivas,
        "luminarias_mantenimiento": luminarias_sin_red,
        "luminaria_detalle": luminaria_detalle,
        "detalle_id": detalle_id,
    }

    return render(request, "luminarias/agregar_luminarias.html", context)


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


#calcula el mes que quiero para el informe, mes actual o algun mes en especifico.
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


def registrar_lecturas(request):
    usuario_id = request.session.get("usuario_id")
    hoy = timezone.localdate()

    redes_disponibles = Red.objects.prefetch_related(
        "zonas",
        "luminarias",
        "lecturas",
    ).order_by("nombre_red")

    if request.method == "POST":
        red_id = request.POST.get("red", "").strip()
        fecha_lectura_raw = request.POST.get("fecha_lectura", "").strip()
        consumo_actual_raw = request.POST.get("consumo_actual", "").strip()

        if not red_id:
            messages.error(request, "Debes seleccionar una red.")
        elif not fecha_lectura_raw:
            messages.error(request, "Debes indicar la fecha de la lectura.")
        elif not consumo_actual_raw:
            messages.error(request, "Debes indicar el consumo actual.")
        else:
            red = redes_disponibles.filter(id_red=red_id).first()

            if not red:
                messages.error(request, "La red seleccionada no está disponible para registrar lecturas.")
            else:
                try:
                    fecha_lectura = date.fromisoformat(fecha_lectura_raw)
                    consumo_actual = Decimal(consumo_actual_raw)
                except (ValueError, ArithmeticError):
                    messages.error(request, "La fecha o el consumo ingresados no son válidos.")
                else:
                    lectura_mensual = RegistrarLectura.objects.filter(
                        red=red,
                        fecha_lectura__year=fecha_lectura.year,
                        fecha_lectura__month=fecha_lectura.month,
                    ).exists()

                    if lectura_mensual:
                        messages.error(request, "Ya existe una lectura registrada para esta red en ese mes.")
                    else:
                        consumo_esperado = red.consumo_esperado or Decimal("0")
                        if consumo_esperado > 0:
                            variacion_consumo = ((consumo_actual - consumo_esperado) / consumo_esperado) * Decimal("100")
                        else:
                            variacion_consumo = Decimal("0")

                        nueva_lectura = RegistrarLectura.objects.create(
                            id_lectura=_siguiente_codigo(RegistrarLectura, "LEC", "id_lectura"),
                            red=red,
                            fecha_lectura=fecha_lectura,
                            consumo_actual=consumo_actual,
                            variacion_consumo=variacion_consumo,
                        )

                        if usuario_id:
                            usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
                            if usuario:
                                Crea.objects.create(usuario=usuario, lectura=nueva_lectura)

                        messages.success(request, "Lectura registrada correctamente.")
                        return redirect("registrar_lecturas")

    detalle_id = request.GET.get("detalle", "").strip()
    red_detalle = None

    if detalle_id:
        red_detalle = redes_disponibles.filter(id_red=detalle_id).first()

    lecturas = RegistrarLectura.objects.select_related("red").order_by("-fecha_lectura", "-id_lectura")

    total_lecturas = lecturas.count()
    lecturas_hoy = lecturas.filter(fecha_lectura=hoy).count()
    total_redes = redes_disponibles.count()

    variacion_total = lecturas.aggregate(total=Sum("variacion_consumo"))["total"] or Decimal("0")
    promedio_variacion = variacion_total / total_lecturas if total_lecturas else Decimal("0")

    lecturas_recientes = []
    for lectura in lecturas[:10]:
        lecturas_recientes.append({
            "lectura": lectura,
            "var_clase": "warning" if abs(lectura.variacion_consumo) >= 10 else ("success" if lectura.variacion_consumo < 0 else "danger"),
        })

    redes_formulario = []
    for red in redes_disponibles:
        ultima_lectura = red.lecturas.order_by("-fecha_lectura", "-id_lectura").first()
        redes_formulario.append({
            "id_red": red.id_red,
            "nombre_red": red.nombre_red,
            "voltaje": red.voltaje,
            "consumo_esperado": red.consumo_esperado,
            "ultima_lectura": ultima_lectura.consumo_actual if ultima_lectura else None,
            "ultima_fecha": ultima_lectura.fecha_lectura if ultima_lectura else None,
            "variacion_ultima": ultima_lectura.variacion_consumo if ultima_lectura else None,
            "zonas": list(red.zonas.all()),
            "total_luminarias": red.luminarias.count(),
        })

    contexto = {
        "total_redes": total_redes,
        "total_lecturas": total_lecturas,
        "lecturas_hoy": lecturas_hoy,
        "promedio_variacion": promedio_variacion,
        "redes_formulario": redes_formulario,
        "lecturas_recientes": lecturas_recientes,
        "red_detalle": red_detalle,
        "fecha_por_defecto": hoy,
        "red_seleccionada": request.POST.get("red", "").strip() if request.method == "POST" else request.GET.get("red", "").strip(),
    }

    return render(request, "luminarias/registrar_lecturas.html", contexto)

base = page_view("base")
base_supervisor = page_view("base_supervisor")
base_tecnicos = page_view("base_tecnicos")
