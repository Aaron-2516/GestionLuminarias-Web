from django.shortcuts import redirect, render

from django.contrib import messages
from django.db.models import Q, Count, Max
import re

from .models import Usuario, Rol, Zona, AsignacionZona, Red, Luminaria, RegistrarLectura
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
    


generar_informe = page_view("generar_informe")
registrar_lecturas = page_view("registrar_lecturas")
agregar_zonas = page_view("agregar_zonas")
agregar_luminarias = page_view("agregar_luminarias")
base = page_view("base")
base_supervisor = page_view("base_supervisor")
base_tecnicos = page_view("base_tecnicos")
