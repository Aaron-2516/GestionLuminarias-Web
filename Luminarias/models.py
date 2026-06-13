from django.db import models


class Rol(models.Model):
    id_rol = models.IntegerField(primary_key=True)
    roles = models.CharField(max_length=50)

    class Meta:
        db_table = "rol"

    def __str__(self):
        return self.roles

class Usuario(models.Model):
    id_usuario = models.CharField(max_length=12, primary_key=True)
    rol = models.ForeignKey(
        Rol,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_rol",
        related_name="usuarios"
    )
    contrasena = models.CharField(max_length=100)
    nombre_usuario = models.CharField(max_length=50)
    apellido_usuario = models.CharField(max_length=50)
    telefono = models.IntegerField()
    estado = models.BooleanField(default=True)
    primer_acceso = models.BooleanField(default=True)

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return f"{self.nombre_usuario} {self.apellido_usuario}"

class Municipio(models.Model):
    id_municipio = models.CharField(max_length=25, primary_key=True)
    nombre_municipio = models.CharField(max_length=50)

    class Meta:
        db_table = "municipio"

    def __str__(self):
        return self.nombre_municipio


class Red(models.Model):
    id_red = models.CharField(max_length=10, primary_key=True)
    nombre_red = models.CharField(max_length=50)
    voltaje = models.DecimalField(max_digits=10, decimal_places=2)
    consumo_esperado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "red"

    def __str__(self):
        return self.nombre_red


class Luminaria(models.Model):
    id_luminaria = models.CharField(max_length=25, primary_key=True)
    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_red",
        related_name="luminarias"
    )
    potencia = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.BooleanField()
    tipo = models.CharField(max_length=50)
    fecha_instalacion = models.DateField()

    class Meta:
        db_table = "luminaria"

    def __str__(self):
        return self.id_luminaria


class RegistrarLectura(models.Model):
    id_lectura = models.CharField(max_length=25, primary_key=True)
    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_red",
        related_name="lecturas"
    )
    fecha_lectura = models.DateField()
    consumo_actual = models.DecimalField(max_digits=10, decimal_places=2)
    variacion_consumo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "registrarlectura"

    def __str__(self):
        return self.id_lectura


class Reporte(models.Model):
    id_reporte = models.CharField(max_length=15, primary_key=True)
    fecha_generacion = models.DateField()
    tipo_reporte = models.IntegerField()
    descripcion = models.CharField(max_length=500)
    formato = models.CharField(max_length=50)
    fecha_fin = models.DateField()
    fecha_inicio = models.DateField()

    class Meta:
        db_table = "reporte"

    def __str__(self):
        return self.id_reporte


class Zona(models.Model):
    id_zona = models.CharField(max_length=25, primary_key=True)
    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_red",
        related_name="zonas"
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_municipio",
        related_name="zonas"
    )
    nombre_zona = models.CharField(max_length=50)
    tipo_zona = models.CharField(max_length=100)

    class Meta:
        db_table = "zona"

    def __str__(self):
        return self.nombre_zona

class AsignacionZona(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="id_usuario",
        related_name="zonas_asignadas"
    )
    zona = models.ForeignKey(
        Zona,
        on_delete=models.RESTRICT,
        db_column="id_zona",
        related_name="tecnicos_asignados"
    )

    class Meta:
        db_table = "asignacion_zona"
        unique_together = ("usuario", "zona")

    def __str__(self):
        return f"{self.usuario} - {self.zona}"


class Crea(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="id_usuario"
    )
    lectura = models.ForeignKey(
        RegistrarLectura,
        on_delete=models.RESTRICT,
        db_column="id_lectura"
    )

    pk = models.CompositePrimaryKey("usuario_id", "lectura_id")

    class Meta:
        db_table = "crea"


class Realiza(models.Model):
    reporte = models.ForeignKey(
        Reporte,
        on_delete=models.RESTRICT,
        db_column="id_reporte"
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="id_usuario"
    )

    pk = models.CompositePrimaryKey("reporte_id", "usuario_id")

    class Meta:
        db_table = "realiza"    