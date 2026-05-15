from django.db import models


class Usuario(models.Model):
    carnet = models.CharField(
        max_length=12,
        primary_key=True
    )
    correo = models.CharField(
        max_length=50
    )
    contrasena = models.CharField(
        max_length=100
    )
    nombre_usuario = models.CharField(
        max_length=50
    )

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return self.nombre_usuario


class Municipio(models.Model):
    id_municipio = models.CharField(
        max_length=25,
        primary_key=True
    )
    nombre_municipio = models.CharField(
        max_length=50
    )

    class Meta:
        db_table = "municipio"

    def __str__(self):
        return self.nombre_municipio


class Red(models.Model):
    id = models.CharField(
        max_length=10,
        primary_key=True
    )
    nombre_red = models.CharField(
        max_length=50
    )
    voltaje = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    class Meta:
        db_table = "red"

    def __str__(self):
        return self.nombre_red


class Zona(models.Model):
    codigo_zona = models.CharField(
        max_length=25,
        primary_key=True
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_municipio",
        related_name="zonas"
    )
    nombre_zona = models.CharField(
        max_length=50
    )

    class Meta:
        db_table = "zona"

    def __str__(self):
        return self.nombre_zona


class Reporte(models.Model):
    id_reporte = models.CharField(
        max_length=15,
        primary_key=True
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="carnet",
        related_name="reportes"
    )
    fecha_generacion = models.DateField()
    tipo_reporte = models.CharField(
        max_length=50
    )
    descripcion = models.CharField(
        max_length=500
    )

    class Meta:
        db_table = "reporte"

    def __str__(self):
        return f"{self.id_reporte} - {self.tipo_reporte}"


class ConsumoEnergia(models.Model):
    codigo_consumo = models.CharField(
        max_length=25,
        primary_key=True
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="carnet",
        related_name="consumos"
    )
    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id",
        related_name="consumos"
    )
    fecha = models.DateField()
    consumo = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    class Meta:
        db_table = "consumo_energia"

    def __str__(self):
        return self.codigo_consumo


class Luminaria(models.Model):
    codigo = models.CharField(
        max_length=25,
        primary_key=True
    )
    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id",
        related_name="luminarias"
    )
    potencia = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )
    estado = models.BooleanField()
    tipo = models.CharField(
        max_length=1024
    )

    class Meta:
        db_table = "luminaria"

    def __str__(self):
        return self.codigo


class Contiene(models.Model):
    pk = models.CompositePrimaryKey("red_id", "zona_id")

    red = models.ForeignKey(
        Red,
        on_delete=models.RESTRICT,
        db_column="id",
        related_name="zonas_asociadas"
    )

    zona = models.ForeignKey(
        Zona,
        on_delete=models.RESTRICT,
        db_column="codigo_zona",
        related_name="redes_asociadas"
    )

    class Meta:
        db_table = "contiene"

    def __str__(self):
        return f"{self.red} - {self.zona}" 
