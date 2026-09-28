import uuid

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .crypto import encrypt_val, is_encrypted
from .audit import get_current_audit_username

ESTADOS = [
    ('ACTIVO', 'Activo'),
    ('LICENCIA', 'En Licencia'),
    ('BAJA', 'Dado de Baja'),
]

ESTADOS_PERFIL = [
    ('ACTIVO', 'Activo'),
    ('INACTIVO', 'Inactivo'),
]

ESTADOS_EQUIPO = [
    ('ASIGNADO', 'Asignado'),
    ('STOCK', 'Stock / Disponible'),
    ('MANTENCION', 'En Mantención'),
    ('BAJA', 'Dado de Baja'),
]

TIPOS_EQUIPO = [
    # EQUIPOS PRINCIPALES
    ('Notebook', 'Notebook'),
    ('Celular', 'Celular'),
    ('Tablet', 'Tablet'),
    ('BAM / Router', 'BAM / Router'),
    ('Mac', 'Mac'),

    # PERIFÉRICOS
    ('Monitor', 'Monitor'),
    ('Adaptador', 'Adaptador'),
    ('Audífonos', 'Audífonos'),
    ('Teclado', 'Teclado'),
    ('Mouse', 'Mouse'),
    ('Docking', 'Docking'),
    ('Otro Periférico', 'Otro Periférico'),
]

ESTADOS_IP = [
    ('LIBRE', 'Libre'),
    ('RESERVADA', 'Reservada'),
]

ESTADOS_ANEXO = [
    ('DISPONIBLE', 'Disponible'),
    ('ASIGNADO', 'Asignado'),
]

def _normalize_spaces(value):
    if value is None:
        return None
    return " ".join(str(value).strip().split())


def _normalize_key(value):
    value = _normalize_spaces(value) or ""
    return value.casefold()


def _normalize_optional_key(value):
    normalized = _normalize_key(value)
    return normalized or None


def _include_derived_update_fields(kwargs, *field_names):
    """Keep internal normalized columns in sync during partial saves."""
    update_fields = kwargs.get('update_fields')
    if update_fields is not None:
        kwargs['update_fields'] = set(update_fields).union(field_names)


class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    nombre_normalizado = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'

    def clean(self):
        self.nombre = _normalize_spaces(self.nombre)
        if not self.nombre:
            raise ValidationError({'nombre': 'El nombre del departamento es obligatorio.'})
        self.nombre_normalizado = _normalize_key(self.nombre)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class SubArea(models.Model):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='subareas',
    )
    nombre = models.CharField(max_length=100)
    nombre_normalizado = models.CharField(
        max_length=100,
        editable=False,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['departamento__nombre', 'nombre']
        verbose_name = 'Subárea'
        verbose_name_plural = 'Subáreas'
        constraints = [
            models.UniqueConstraint(
                fields=['departamento', 'nombre_normalizado'],
                name='uniq_subarea_departamento_nombre_norm',
            )
        ]

    def clean(self):
        self.nombre = _normalize_spaces(self.nombre)
        if not self.nombre:
            raise ValidationError({'nombre': 'El nombre de la subárea es obligatorio.'})
        self.nombre_normalizado = _normalize_key(self.nombre)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.departamento.nombre} / {self.nombre}"


class Usuario(models.Model):
    nombre_completo = models.CharField(max_length=150)
    nombre_completo_normalizado = models.CharField(
        max_length=150,
        unique=True,
        editable=False,
    )
    usuario_red = models.CharField(max_length=50, unique=True)
    usuario_red_normalizado = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
    )
    correo_corp = models.EmailField(unique=True)
    correo_corp_normalizado = models.EmailField(
        unique=True,
        editable=False,
    )
    dpto_area = models.CharField(max_length=100, blank=True, default='')
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='usuarios',
    )
    subarea = models.ForeignKey(
        SubArea,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
    )
    cargo = models.CharField(max_length=100, null=True, blank=True)
    hostname = models.CharField(max_length=50, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO', null=True, blank=True)
    
    gmail = models.EmailField(null=True, blank=True)
    password_gmail = models.CharField(max_length=255, null=True, blank=True)
    celular = models.CharField(max_length=30, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    anexo = models.CharField(max_length=10, null=True, blank=True)
    sif = models.BooleanField(default=False)
    vpn_cisco = models.BooleanField(default=False)
    password_vpn = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['estado', 'departamento'],
                name='idx_usr_estado_dpto',
            ),
        ]

    def clean(self):
        if not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento del usuario.'
            })

        if self.subarea_id and not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento de la subárea seleccionada.'
            })

        if self.subarea_id and self.departamento_id:
            if self.subarea.departamento_id != self.departamento_id:
                raise ValidationError({
                    'subarea': 'La subárea seleccionada no pertenece al departamento indicado.'
                })

    def save(self, *args, **kwargs):
        self.nombre_completo = _normalize_spaces(self.nombre_completo) or ''
        self.usuario_red = (_normalize_spaces(self.usuario_red) or '').lower()
        self.correo_corp = (_normalize_spaces(self.correo_corp) or '').lower()
        self.dpto_area = _normalize_spaces(self.dpto_area) or ''
        self.cargo = _normalize_spaces(self.cargo) if self.cargo else self.cargo
        self.hostname = _normalize_spaces(self.hostname) if self.hostname else self.hostname
        self.gmail = (_normalize_spaces(self.gmail) or '').lower() if self.gmail else self.gmail
        self.celular = _normalize_spaces(self.celular) if self.celular else self.celular
        self.telefono = _normalize_spaces(self.telefono) if self.telefono else self.telefono
        self.anexo = _normalize_spaces(self.anexo) if self.anexo else self.anexo
        self.nombre_completo_normalizado = _normalize_key(self.nombre_completo)
        self.usuario_red_normalizado = _normalize_key(self.usuario_red)
        self.correo_corp_normalizado = _normalize_key(self.correo_corp)

        _include_derived_update_fields(
            kwargs,
            'nombre_completo_normalizado',
            'usuario_red_normalizado',
            'correo_corp_normalizado',
        )

        if self.departamento_id:
            self.dpto_area = self.departamento.nombre

        self.clean()

        if self.password_gmail and not is_encrypted(self.password_gmail):
            self.password_gmail = encrypt_val(self.password_gmail)

        if self.password_vpn and not is_encrypted(self.password_vpn):
            self.password_vpn = encrypt_val(self.password_vpn)

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_completo} ({self.usuario_red})"

class Anexo(models.Model):
    numero_anexo = models.CharField(
        max_length=10,
        unique=True
    )

    exterior = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anexo_asignado'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_ANEXO,
        default='DISPONIBLE'
    )

    observaciones = models.TextField(
        null=True,
        blank=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        self.estado = (
            'ASIGNADO'
            if self.usuario_id
            else 'DISPONIBLE'
        )

    def save(self, *args, **kwargs):
        self.numero_anexo = _normalize_spaces(self.numero_anexo) or ''
        self.clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    class Meta:
        ordering = ['numero_anexo']
        indexes = [
            models.Index(
                fields=['estado', 'numero_anexo'],
                name='idx_anexo_estado_num',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        usuario__isnull=True,
                        estado='DISPONIBLE',
                    )
                    | models.Q(
                        usuario__isnull=False,
                        estado='ASIGNADO',
                    )
                ),
                name='ck_anexo_asignacion_valida',
            ),
        ]

    def __str__(self):
        return f"{self.numero_anexo} - {self.estado}"


class HistorialAnexo(models.Model):
    anexo = models.ForeignKey(
        Anexo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial'
    )

    usuario_anterior = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    usuario_nuevo = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    fecha_movimiento = models.DateTimeField(
        auto_now_add=True
    )

    accion = models.CharField(
        max_length=50,
        default='MODIFICACION'
    )

    modificado_por = models.CharField(
    max_length=150,
    null=True,
    blank=True
)

    observacion = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.anexo.numero_anexo} - {self.accion}"

class IP(models.Model):
    direccion_ip = models.GenericIPAddressField(unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_IP, default='LIBRE')
    observacion = models.CharField(max_length=255, null=True, blank=True)
    usuario = models.OneToOneField(
    Usuario,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='ip'
)
    asignado_otro = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        verbose_name = 'IP'
        verbose_name_plural = 'IPs'
        ordering = ['direccion_ip']
        indexes = [
            models.Index(
                fields=['estado', 'direccion_ip'],
                name='idx_ip_estado_dir',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            estado='LIBRE',
                            usuario__isnull=True,
                        )
                        & (
                            models.Q(asignado_otro__isnull=True)
                            | models.Q(asignado_otro='')
                        )
                    )
                    | (
                        models.Q(
                            estado='RESERVADA',
                            usuario__isnull=False,
                        )
                        & (
                            models.Q(asignado_otro__isnull=True)
                            | models.Q(asignado_otro='')
                        )
                    )
                    | (
                        models.Q(
                            estado='RESERVADA',
                            usuario__isnull=True,
                            asignado_otro__isnull=False,
                        )
                        & ~models.Q(asignado_otro='')
                    )
                ),
                name='ck_ip_estado_propietario',
            ),
        ]

    def __str__(self):
        return f"{self.direccion_ip} - {self.estado}"

    def clean(self):
        self.asignado_otro = _normalize_spaces(self.asignado_otro) or None
        if self.usuario_id:
            self.asignado_otro = None
            self.estado = 'RESERVADA'
        elif self.asignado_otro:
            self.estado = 'RESERVADA'
        else:
            self.estado = 'LIBRE'

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            from .services.asignacion_ips import sync_ip_assignment_from_legacy
            sync_ip_assignment_from_legacy(self.pk)

# =========================================
# SERVIDORES
# =========================================

class Servidor(models.Model):
    ip = models.OneToOneField(
        IP,
        on_delete=models.PROTECT,
        related_name='servidor',
        null=True,
        blank=True,
    )

    hostname = models.CharField(
        max_length=100,
        unique=True
    )
    hostname_normalizado = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )

    descripcion = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['hostname']
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'

    def save(self, *args, **kwargs):
        self.hostname = _normalize_spaces(self.hostname) or ''
        self.hostname_normalizado = _normalize_key(self.hostname)
        _include_derived_update_fields(kwargs, 'hostname_normalizado')
        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        direccion_ip = self.ip.direccion_ip if self.ip_id else 'Sin IP'
        return f"{self.hostname} - {direccion_ip}"


class HistorialServidor(models.Model):
    servidor = models.ForeignKey(
        Servidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial',
    )
    servidor_hostname = models.CharField(max_length=100)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=50, default='MODIFICACION')
    modificado_por = models.CharField(max_length=150, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento', '-pk']
        indexes = [
            models.Index(
                fields=['servidor', '-fecha_movimiento'],
                name='idx_hist_srv_fecha',
            ),
        ]


class HistorialUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='historial')
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=50, default='MODIFICACION')
    modificado_por = models.CharField(max_length=150,null=True,blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento']


class Equipamiento(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipos'
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPOS_EQUIPO,
        default='Notebook'
    )

    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    numero_serie = models.CharField(
    max_length=20,
    unique=True,
    null=True,
    blank=True
)
    numero_serie_normalizado = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    hostname = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    hostname_computador_normalizado = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )


    af = models.CharField(
        max_length=12,
        null=True,
        blank=True
    )
    af_normalizado = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    accesorios = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    fecha_asignacion = models.DateField(
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_EQUIPO,
        default='ASIGNADO'
    )

    numero_telefono = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    imei = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    pin = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    icloud_cuenta = models.EmailField(
        null=True,
        blank=True
    )

    icloud_password = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=['tipo', 'estado'],
                name='idx_equipo_tipo_estado',
            ),
            models.Index(
                fields=['usuario', 'tipo'],
                name='idx_equipo_usr_tipo',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        usuario__isnull=True,
                        fecha_asignacion__isnull=True,
                        estado__in=['STOCK', 'MANTENCION', 'BAJA'],
                    )
                    | models.Q(
                        usuario__isnull=False,
                        estado__in=['ASIGNADO', 'MANTENCION', 'BAJA'],
                    )
                ),
                name='ck_equipo_asignacion_valida',
            ),
        ]

    def clean(self):
        if not self.usuario_id:
            if self.estado == 'ASIGNADO':
                self.estado = 'STOCK'
            self.fecha_asignacion = None
        elif self.estado == 'STOCK':
            self.estado = 'ASIGNADO'

    def save(self, *args, **kwargs):

        self.numero_serie = _normalize_spaces(self.numero_serie) or None
        self.hostname = _normalize_spaces(self.hostname) or None
        self.af = _normalize_spaces(self.af) or None

        # =====================================
        # COHERENCIA DE ASIGNACIÓN
        # =====================================

        self.clean()


        # =====================================
        # SINCRONIZAR HOSTNAME
        # Usuario -> Notebook / Mac
        # =====================================

        if (
            self.usuario_id and
            self.tipo in ['Notebook', 'Mac']
        ):
            self.hostname = (
                self.usuario.hostname.strip()
                if self.usuario.hostname
                else None
            )

        self.numero_serie_normalizado = _normalize_optional_key(
            self.numero_serie
        )
        self.af_normalizado = _normalize_optional_key(self.af)
        self.hostname_computador_normalizado = (
            _normalize_optional_key(self.hostname)
            if self.tipo in ['Notebook', 'Mac']
            else None
        )
        _include_derived_update_fields(
            kwargs,
            'numero_serie_normalizado',
            'af_normalizado',
            'hostname_computador_normalizado',
        )


        # =====================================
        # ENCRIPTAR SECRETOS DEL EQUIPO
        # =====================================
        if self.pin and not is_encrypted(self.pin):
            self.pin = encrypt_val(self.pin)

        if self.icloud_password and not is_encrypted(self.icloud_password):
            self.icloud_password = encrypt_val(self.icloud_password)

        with transaction.atomic():
            super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.tipo} - {self.marca} {self.modelo} ({self.numero_serie})"


class HistorialEquipo(models.Model):
    equipo = models.ForeignKey(
        Equipamiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial'
    )
    usuario_anterior = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )
    usuario_nuevo = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )
    fecha_movimiento = models.DateTimeField(
        auto_now_add=True
    )
    accion = models.CharField(
        max_length=50,
        default='MODIFICACION'
    )

    modificado_por = models.CharField(
    max_length=150,
    null=True,
    blank=True
)
    observacion = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-fecha_movimiento']

class PerfilGenerico(models.Model):
    nombre = models.CharField(max_length=150, null=True, blank=True)
    usuario = models.CharField(max_length=100, unique=True)
    usuario_normalizado = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )
    password = models.CharField(max_length=255, null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    # Campo legado conservado temporalmente para compatibilidad con datos
    # anteriores e importadores. La fuente estructurada es departamento/subarea.
    dpto_area = models.CharField(max_length=100, blank=True, default='')
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='perfiles_genericos',
    )
    subarea = models.ForeignKey(
        SubArea,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='perfiles_genericos',
    )
    tipo = models.CharField(max_length=20, default='On Premise')
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_PERFIL,
        default='ACTIVO',
    )
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        ordering = [
            'departamento__nombre',
            'subarea__nombre',
            'nombre',
            'usuario',
        ]
        indexes = [
            models.Index(
                fields=['estado', 'departamento'],
                name='idx_perfil_estado_dpto',
            ),
        ]

    def clean(self):
        if not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento del perfil.'
            })

        if self.subarea_id and not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento de la subárea seleccionada.'
            })

        if self.subarea_id and self.departamento_id:
            if self.subarea.departamento_id != self.departamento_id:
                raise ValidationError({
                    'subarea': 'La subárea seleccionada no pertenece al departamento indicado.'
                })

    def save(self, *args, **kwargs):
        self.nombre = _normalize_spaces(self.nombre) if self.nombre else self.nombre
        self.usuario = _normalize_spaces(self.usuario) or ''
        self.correo = (_normalize_spaces(self.correo) or '').lower() or None
        self.usuario_normalizado = _normalize_key(self.usuario)
        _include_derived_update_fields(kwargs, 'usuario_normalizado')
        self.observaciones = (
            _normalize_spaces(self.observaciones)
            if self.observaciones
            else self.observaciones
        )

        if self.subarea_id:
            self.dpto_area = self.subarea.nombre
        elif self.departamento_id:
            self.dpto_area = self.departamento.nombre
        else:
            self.dpto_area = _normalize_spaces(self.dpto_area) or ''

        self.clean()

        if self.password and not is_encrypted(self.password):
            self.password = encrypt_val(self.password)

        with transaction.atomic():
            super().save(*args, **kwargs)


class HistorialPerfilGenerico(models.Model):
    perfil = models.ForeignKey(
        PerfilGenerico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial',
    )
    perfil_nombre = models.CharField(max_length=150)
    perfil_usuario = models.CharField(max_length=100)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=50, default='MODIFICACION')
    modificado_por = models.CharField(max_length=150, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento', '-pk']
        indexes = [
            models.Index(
                fields=['perfil', '-fecha_movimiento'],
                name='idx_hist_perfil_fecha',
            ),
        ]


class PCGenerico(models.Model):
    ip = models.OneToOneField(
        IP,
        on_delete=models.PROTECT,
        related_name='pc_generico',
        null=True,
        blank=True,
    )

    usuario_local = models.CharField(
        max_length=150
    )

    password = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    hostname = models.CharField(
        max_length=100,
        unique=True
    )
    hostname_normalizado = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )

    dpto_area = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='pcs_genericos',
    )
    subarea = models.ForeignKey(
        SubArea,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pcs_genericos',
    )

    marca = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    modelo = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    numero_serie = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )
    numero_serie_normalizado = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    activo_fijo = models.CharField(
        max_length=12,
        null=True,
        blank=True
    )
    activo_fijo_normalizado = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    teamviewer_id = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    observaciones = models.TextField(
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        self.usuario_local = _normalize_spaces(self.usuario_local) or ''
        self.hostname = _normalize_spaces(self.hostname) or ''
        self.numero_serie = _normalize_spaces(self.numero_serie) or None
        self.activo_fijo = _normalize_spaces(self.activo_fijo) or None
        self.hostname_normalizado = _normalize_key(self.hostname)
        self.numero_serie_normalizado = _normalize_optional_key(
            self.numero_serie
        )
        self.activo_fijo_normalizado = _normalize_optional_key(
            self.activo_fijo
        )
        _include_derived_update_fields(
            kwargs,
            'hostname_normalizado',
            'numero_serie_normalizado',
            'activo_fijo_normalizado',
        )

        if not self.departamento_id and self.dpto_area:
            normalized_area = _normalize_key(self.dpto_area)
            self.departamento = Departamento.objects.filter(
                nombre_normalizado=normalized_area
            ).first()

        if self.subarea_id:
            self.dpto_area = self.subarea.nombre
        elif self.departamento_id:
            self.dpto_area = self.departamento.nombre
        else:
            self.dpto_area = _normalize_spaces(self.dpto_area)

        self.clean()

        if self.password and not is_encrypted(self.password):
            self.password = encrypt_val(self.password)

        with transaction.atomic():
            super().save(*args, **kwargs)

    def clean(self):
        if not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento del PC genérico.'
            })

        if self.subarea_id and not self.departamento_id:
            raise ValidationError({
                'departamento': 'Debe indicar el departamento de la subárea seleccionada.'
            })
        if (
            self.subarea_id
            and self.departamento_id
            and self.subarea.departamento_id != self.departamento_id
        ):
            raise ValidationError({
                'subarea': 'La subárea seleccionada no pertenece al departamento indicado.'
            })

    class Meta:
        ordering = ['hostname']
        indexes = [
            models.Index(
                fields=['departamento', 'subarea'],
                name='idx_pc_generico_dpto_sub',
            ),
        ]

    def __str__(self):
        return f"{self.hostname} - {self.usuario_local}"


class TipoAsignacionIP(models.TextChoices):
    USUARIO = 'USUARIO', 'Usuario'
    SERVIDOR = 'SERVIDOR', 'Servidor'
    PC_GENERICO = 'PC_GENERICO', 'PC Genérico'
    OTRO = 'OTRO', 'Otro dispositivo o servicio'


class AsignacionIP(models.Model):
    """Propietario formal y único de una dirección IP administrada."""

    ip = models.OneToOneField(
        IP,
        on_delete=models.CASCADE,
        related_name='asignacion_activa',
    )
    tipo = models.CharField(max_length=20, choices=TipoAsignacionIP.choices)
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='asignacion_ip_activa',
        null=True,
        blank=True,
    )
    servidor = models.OneToOneField(
        Servidor,
        on_delete=models.CASCADE,
        related_name='asignacion_ip_activa',
        null=True,
        blank=True,
    )
    pc_generico = models.OneToOneField(
        PCGenerico,
        on_delete=models.CASCADE,
        related_name='asignacion_ip_activa',
        null=True,
        blank=True,
    )
    detalle = models.CharField(max_length=150, null=True, blank=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación IP activa'
        verbose_name_plural = 'Asignaciones IP activas'
        ordering = ['ip__direccion_ip']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        tipo=TipoAsignacionIP.USUARIO,
                        usuario__isnull=False,
                        servidor__isnull=True,
                        pc_generico__isnull=True,
                        detalle__isnull=True,
                    )
                    | models.Q(
                        tipo=TipoAsignacionIP.SERVIDOR,
                        usuario__isnull=True,
                        servidor__isnull=False,
                        pc_generico__isnull=True,
                        detalle__isnull=True,
                    )
                    | models.Q(
                        tipo=TipoAsignacionIP.PC_GENERICO,
                        usuario__isnull=True,
                        servidor__isnull=True,
                        pc_generico__isnull=False,
                        detalle__isnull=True,
                    )
                    | (
                        models.Q(
                            tipo=TipoAsignacionIP.OTRO,
                            usuario__isnull=True,
                            servidor__isnull=True,
                            pc_generico__isnull=True,
                            detalle__isnull=False,
                        )
                        & ~models.Q(detalle='')
                    )
                ),
                name='ck_asignacion_ip_propietario_valido',
            ),
        ]

    @property
    def propietario_nombre(self):
        if self.tipo == TipoAsignacionIP.USUARIO and self.usuario_id:
            return self.usuario.nombre_completo
        if self.tipo == TipoAsignacionIP.SERVIDOR and self.servidor_id:
            return self.servidor.hostname
        if self.tipo == TipoAsignacionIP.PC_GENERICO and self.pc_generico_id:
            return self.pc_generico.hostname
        return self.detalle

    def __str__(self):
        return f'{self.ip.direccion_ip} - {self.propietario_nombre}'


class HistorialAsignacionIP(models.Model):
    ACCIONES = [
        ('ASIGNACION', 'Asignación'),
        ('LIBERACION', 'Liberación'),
        ('MIGRACION', 'Migración inicial'),
    ]

    ip = models.ForeignKey(
        IP,
        on_delete=models.SET_NULL,
        related_name='historial_asignaciones',
        null=True,
        blank=True,
    )
    direccion_ip = models.GenericIPAddressField()
    accion = models.CharField(max_length=20, choices=ACCIONES)
    tipo = models.CharField(
        max_length=20,
        choices=TipoAsignacionIP.choices,
        null=True,
        blank=True,
    )
    propietario_id = models.PositiveBigIntegerField(null=True, blank=True)
    propietario_nombre = models.CharField(max_length=150, null=True, blank=True)
    realizado_por = models.CharField(max_length=150, null=True, blank=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de asignación IP'
        verbose_name_plural = 'Historial de asignaciones IP'
        ordering = ['-fecha_movimiento', '-pk']
        indexes = [
            models.Index(
                fields=['direccion_ip', '-fecha_movimiento'],
                name='idx_hist_ip_direccion_fecha',
            ),
        ]

    def __str__(self):
        return f'{self.direccion_ip} - {self.accion}'


class HistorialPCGenerico(models.Model):
    pc = models.ForeignKey(
        PCGenerico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial'
    )

    accion = models.CharField(
        max_length=50,
        default='MODIFICACION'
    )

    modificado_por = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    observacion = models.TextField(
        null=True,
        blank=True
    )

    fecha_movimiento = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.pc.hostname} - {self.accion}"



class SecurityAuditLog(models.Model):
    event = models.CharField(max_length=80)
    actor = models.CharField(max_length=150, null=True, blank=True)
    module = models.CharField(max_length=80, null=True, blank=True)
    object_id_text = models.CharField(max_length=80, null=True, blank=True)
    secret_type = models.CharField(max_length=80, null=True, blank=True)
    success = models.BooleanField(default=False)
    detail = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class PortalSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='portal_sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_revoked(self):
        return self.revoked_at is not None

# --- HISTORIAL DE PERFILES GENERICOS ---

@receiver(pre_save, sender=PerfilGenerico)
def track_historial_perfil_generico(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        perfil_previo = PerfilGenerico.objects.select_related(
            'departamento',
            'subarea',
        ).get(pk=instance.pk)
    except PerfilGenerico.DoesNotExist:
        return

    cambios = []

    def add_cambio(campo, anterior, actual):
        if str(anterior) != str(actual):
            cambios.append(
                f"{campo}:::{anterior or 'N/I'}:::{actual or 'N/I'}"
            )

    add_cambio('Nombre / Perfil', perfil_previo.nombre, instance.nombre)
    add_cambio('Usuario', perfil_previo.usuario, instance.usuario)
    add_cambio('Tipo de cuenta', perfil_previo.tipo, instance.tipo)
    add_cambio('Correo', perfil_previo.correo, instance.correo)
    add_cambio(
        'Departamento',
        perfil_previo.departamento.nombre,
        instance.departamento.nombre,
    )
    add_cambio(
        'SubÃ¡rea',
        perfil_previo.subarea.nombre if perfil_previo.subarea_id else None,
        instance.subarea.nombre if instance.subarea_id else None,
    )
    add_cambio('Estado', perfil_previo.estado, instance.estado)
    add_cambio(
        'Observaciones',
        perfil_previo.observaciones,
        instance.observaciones,
    )

    if perfil_previo.password != instance.password:
        cambios.append(
            'ContraseÃ±a:::â€¢â€¢â€¢â€¢:::â€¢â€¢â€¢â€¢'
        )

    if cambios:
        HistorialPerfilGenerico.objects.create(
            perfil=instance,
            perfil_nombre=instance.nombre or instance.usuario,
            perfil_usuario=instance.usuario,
            accion='MODIFICACION',
            modificado_por=get_current_audit_username(),
            observacion='||'.join(cambios),
        )


@receiver(post_save, sender=PerfilGenerico)
def registrar_creacion_perfil_generico(sender, instance, created, **kwargs):
    if not created:
        return

    HistorialPerfilGenerico.objects.create(
        perfil=instance,
        perfil_nombre=instance.nombre or instance.usuario,
        perfil_usuario=instance.usuario,
        accion='CREACION',
        modificado_por=get_current_audit_username(),
        observacion=(
            f'Perfil genÃ©rico creado - Usuario: {instance.usuario} - '
            f'Estado: {instance.estado}'
        ),
    )


@receiver(pre_delete, sender=PerfilGenerico)
def registrar_eliminacion_perfil_generico(sender, instance, **kwargs):
    HistorialPerfilGenerico.objects.create(
        perfil=instance,
        perfil_nombre=instance.nombre or instance.usuario,
        perfil_usuario=instance.usuario,
        accion='ELIMINACION',
        modificado_por=get_current_audit_username(),
        observacion=(
            f'Perfil genÃ©rico eliminado - Usuario: {instance.usuario} - '
            f'Estado final: {instance.estado}'
        ),
    )


# --- HISTORIAL DE PCs GENERICOS ---

@receiver(pre_save, sender=PCGenerico)
def track_historial_pc_generico(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        pc_previo = PCGenerico.objects.select_related(
            'departamento',
            'subarea',
            'ip',
        ).get(pk=instance.pk)
    except PCGenerico.DoesNotExist:
        return

    cambios = []

    def add_cambio(campo, anterior, actual):
        if str(anterior) != str(actual):
            cambios.append(
                f"{campo}:::{anterior or 'N/I'}:::{actual or 'N/I'}"
            )

    add_cambio(
        "Usuario Local",
        pc_previo.usuario_local,
        instance.usuario_local
    )

    add_cambio(
        "Hostname",
        pc_previo.hostname,
        instance.hostname
    )

    add_cambio(
        "Departamento",
        (
            pc_previo.departamento.nombre
            if pc_previo.departamento_id
            else pc_previo.dpto_area
        ),
        (
            instance.departamento.nombre
            if instance.departamento_id
            else instance.dpto_area
        ),
    )

    add_cambio(
        "Subárea",
        pc_previo.subarea.nombre if pc_previo.subarea_id else None,
        instance.subarea.nombre if instance.subarea_id else None,
    )

    add_cambio(
        "Marca",
        pc_previo.marca,
        instance.marca
    )

    add_cambio(
        "Modelo",
        pc_previo.modelo,
        instance.modelo
    )

    add_cambio(
        "Número de Serie",
        pc_previo.numero_serie,
        instance.numero_serie
    )

    add_cambio(
        "Activo Fijo",
        pc_previo.activo_fijo,
        instance.activo_fijo
    )

    add_cambio(
        "ID TeamViewer",
        pc_previo.teamviewer_id,
        instance.teamviewer_id
    )
    add_cambio(
        "Dirección IP",
        pc_previo.ip.direccion_ip if pc_previo.ip_id else None,
        instance.ip.direccion_ip if instance.ip_id else None,
    )
    add_cambio(
            "Observaciones",
            pc_previo.observaciones,
            instance.observaciones
        )

    # El serializer conserva el valor cifrado si el campo llega vacío,
    # por lo que se puede comparar sin descifrar ni exponer el secreto.
    if pc_previo.password != instance.password:
        cambios.append("Contraseña:::••••••••:::••••••••")

    if cambios:
        HistorialPCGenerico.objects.create(
            pc=instance,
            accion="MODIFICACION",
            modificado_por=get_current_audit_username(),
            observacion="||".join(cambios)
        )


@receiver(post_save, sender=PCGenerico)
def registrar_creacion_pc_generico(
    sender,
    instance,
    created,
    **kwargs
):
    if not created:
        return

    HistorialPCGenerico.objects.create(
        pc=instance,
        accion="CREACION",
        modificado_por=get_current_audit_username(),
        observacion=(
            f"PC Genérico creado - "
            f"Hostname: {instance.hostname}"
        )
    )

# --- HISTORIAL DE ANEXOS ---

@receiver(pre_save, sender=Anexo)
def track_historial_anexo(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        anexo_previo = Anexo.objects.get(pk=instance.pk)
    except Anexo.DoesNotExist:
        return

    cambios = []

    def add_cambio(campo, anterior, actual):
        if str(anterior) != str(actual):
            cambios.append(
                f"{campo}:::{anterior or 'N/I'}:::{actual or 'N/I'}"
            )

    usuario_anterior = (
        anexo_previo.usuario.nombre_completo
        if anexo_previo.usuario
        else "Sin asignar"
    )

    usuario_nuevo = (
        instance.usuario.nombre_completo
        if instance.usuario
        else "Sin asignar"
    )

    add_cambio(
        "Número Anexo",
        anexo_previo.numero_anexo,
        instance.numero_anexo
    )

    add_cambio(
        "Exterior",
        anexo_previo.exterior,
        instance.exterior
    )

    add_cambio(
        "Usuario Asignado",
        usuario_anterior,
        usuario_nuevo
    )

    add_cambio(
        "Estado",
        anexo_previo.estado,
        instance.estado
    )

    add_cambio(
        "Observaciones",
        anexo_previo.observaciones,
        instance.observaciones
    )

    if cambios:
        HistorialAnexo.objects.create(
        anexo=instance,
        usuario_anterior=usuario_anterior,
        usuario_nuevo=usuario_nuevo,
        accion="MODIFICACION",
        modificado_por=get_current_audit_username(),
        observacion="||".join(cambios)
    )


@receiver(post_save, sender=Anexo)
def registrar_creacion_anexo(sender, instance, created, **kwargs):
    if not created:
        return

    usuario_nuevo = (
        instance.usuario.nombre_completo
        if instance.usuario
        else "Sin asignar"
    )

    HistorialAnexo.objects.create(
        anexo=instance,
        usuario_anterior="Sin asignar",
        usuario_nuevo=usuario_nuevo,
        accion="CREACION",
        modificado_por=get_current_audit_username(),
        observacion=(
            f"Anexo creado con estado {instance.estado}"
        )
    )     

# --- HISTORIAL DE EQUIPAMIENTO ---

@receiver(pre_save, sender=Equipamiento)
def track_historial_equipo(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        equipo_previo = Equipamiento.objects.get(pk=instance.pk)
    except Equipamiento.DoesNotExist:
        return

    cambios = []

    def add_cambio(campo, anterior, actual):
        if str(anterior) != str(actual):
            cambios.append(
                f"{campo}:::{anterior or 'N/I'}:::{actual or 'N/I'}"
            )

    add_cambio(
        "Tipo",
        equipo_previo.tipo,
        instance.tipo
    )

    add_cambio(
        "Marca",
        equipo_previo.marca,
        instance.marca
    )

    add_cambio(
        "Modelo",
        equipo_previo.modelo,
        instance.modelo
    )

    add_cambio(
        "Número de Serie",
        equipo_previo.numero_serie,
        instance.numero_serie
    )

    add_cambio(
        "Hostname",
        equipo_previo.hostname,
        instance.hostname
    )

    add_cambio(
        "AF",
        equipo_previo.af,
        instance.af
    )

    add_cambio(
        "Estado",
        equipo_previo.estado,
        instance.estado
    )

    add_cambio(
        "Fecha Asignación",
        equipo_previo.fecha_asignacion,
        instance.fecha_asignacion
    )

    add_cambio(
        "Número Teléfono",
        equipo_previo.numero_telefono,
        instance.numero_telefono
    )

    add_cambio(
        "IMEI",
        equipo_previo.imei,
        instance.imei
    )

    if equipo_previo.pin != instance.pin:
        add_cambio("PIN", "••••••••", "••••••••")

    add_cambio(
        "Cuenta iCloud",
        equipo_previo.icloud_cuenta,
        instance.icloud_cuenta
    )

    if equipo_previo.icloud_password != instance.icloud_password:
        add_cambio(
            "Contraseña iCloud",
            "••••••••",
            "••••••••"
        )

    usuario_anterior = (
        equipo_previo.usuario.nombre_completo
        if equipo_previo.usuario
        else "Sin asignar"
    )

    usuario_nuevo = (
        instance.usuario.nombre_completo
        if instance.usuario
        else "Sin asignar"
    )

    add_cambio(
        "Usuario Asignado",
        usuario_anterior,
        usuario_nuevo
    )

    if cambios:
        HistorialEquipo.objects.create(
            equipo=instance,
            usuario_anterior=usuario_anterior,
            usuario_nuevo=usuario_nuevo,
            accion="MODIFICACION",
            modificado_por=get_current_audit_username(),
            observacion="||".join(cambios)
        )

# --- SINCRONIZACIÓN Y RESTRICCIÓN DE DUPLICIDAD IP ---

@receiver(pre_save, sender=IP)
def sync_ip_con_usuario(sender, instance, **kwargs):

    # IP asignada directamente a un usuario
    if instance.usuario_id:

        # Una IP de usuario no puede estar reservada para "Otro"
        instance.asignado_otro = None

        # Toda IP asociada a un usuario queda como RESERVADA
        instance.estado = 'RESERVADA'

        # Un usuario solo puede tener una IP.
        # Si ya tenía otra, liberarla antes de guardar la nueva.
        IP.objects.filter(
            usuario_id=instance.usuario_id
        ).exclude(
            pk=instance.pk
        ).update(
            usuario=None,
            estado='LIBRE',
            asignado_otro=None
        )

        # IP reservada para impresora, servidor, CCTV, etc.
    elif instance.asignado_otro and instance.asignado_otro.strip():

        instance.estado = 'RESERVADA'

       # IP sin usuario ni otro dispositivo
    else:

            instance.estado = 'LIBRE'


@receiver(pre_save, sender=Servidor)
def track_historial_servidor(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        servidor_previo = Servidor.objects.select_related('ip').get(
            pk=instance.pk
        )
    except Servidor.DoesNotExist:
        return

    cambios = []

    def add_cambio(campo, anterior, actual):
        if str(anterior) != str(actual):
            cambios.append(
                f"{campo}:::{anterior or 'N/I'}:::{actual or 'N/I'}"
            )

    add_cambio('Hostname', servidor_previo.hostname, instance.hostname)
    add_cambio(
        'DirecciÃ³n IP',
        servidor_previo.ip.direccion_ip if servidor_previo.ip_id else None,
        instance.ip.direccion_ip if instance.ip_id else None,
    )
    add_cambio(
        'DescripciÃ³n',
        servidor_previo.descripcion,
        instance.descripcion,
    )

    if cambios:
        HistorialServidor.objects.create(
            servidor=instance,
            servidor_hostname=instance.hostname,
            accion='MODIFICACION',
            modificado_por=get_current_audit_username(),
            observacion='||'.join(cambios),
        )


@receiver(post_save, sender=Servidor)
def registrar_creacion_servidor(sender, instance, created, **kwargs):
    if not created:
        return

    direccion_ip = instance.ip.direccion_ip if instance.ip_id else 'Sin IP'
    HistorialServidor.objects.create(
        servidor=instance,
        servidor_hostname=instance.hostname,
        accion='CREACION',
        modificado_por=get_current_audit_username(),
        observacion=(
            f'Servidor creado - Hostname: {instance.hostname} - '
            f'IP: {direccion_ip}'
        ),
    )


@receiver(pre_delete, sender=Servidor)
def registrar_eliminacion_servidor(sender, instance, **kwargs):
    direccion_ip = instance.ip.direccion_ip if instance.ip_id else 'Sin IP'
    HistorialServidor.objects.create(
        servidor=instance,
        servidor_hostname=instance.hostname,
        accion='ELIMINACION',
        modificado_por=get_current_audit_username(),
        observacion=(
            f'Servidor eliminado - Hostname: {instance.hostname} - '
            f'IP liberada: {direccion_ip}'
        ),
    )


@receiver(pre_delete, sender=Servidor)
def liberar_ip_al_eliminar_servidor(sender, instance, **kwargs):
    if not instance.ip_id:
        return

    from .services.asignacion_ips import release_ip_for_owner
    release_ip_for_owner(
        instance.ip_id,
        TipoAsignacionIP.SERVIDOR,
        instance.pk,
    )


@receiver(pre_delete, sender=PCGenerico)
def liberar_ip_al_eliminar_pc_generico(sender, instance, **kwargs):
    if not instance.ip_id:
        return

    from .services.asignacion_ips import release_ip_for_owner
    release_ip_for_owner(
        instance.ip_id,
        TipoAsignacionIP.PC_GENERICO,
        instance.pk,
    )


@receiver(pre_save, sender=Usuario)
def track_historial_usuario(sender, instance, **kwargs):
    if instance.pk:
        try:
            usr_previo = Usuario.objects.get(pk=instance.pk)
        except Usuario.DoesNotExist:
            usr_previo = None

        if usr_previo:
            cambios = []
            def add_cambio(campo, ant, act):
                if str(ant) != str(act):
                    cambios.append(f"{campo}:::{ant or 'N/I'}:::{act or 'N/I'}")

            add_cambio("Nombre Completo", usr_previo.nombre_completo, instance.nombre_completo)
            add_cambio("Estado", usr_previo.estado, instance.estado)
            add_cambio("Hostname", usr_previo.hostname, instance.hostname)
            add_cambio("Cargo", usr_previo.cargo, instance.cargo)
            add_cambio("Departamento", usr_previo.dpto_area, instance.dpto_area)
            add_cambio(
                "Departamento (catálogo)",
                usr_previo.departamento.nombre if usr_previo.departamento else None,
                instance.departamento.nombre if instance.departamento else None
            )
            add_cambio(
                "Subárea",
                usr_previo.subarea.nombre if usr_previo.subarea else None,
                instance.subarea.nombre if instance.subarea else None
            )
            add_cambio("Usuario Red", usr_previo.usuario_red, instance.usuario_red)
            add_cambio("Correo Corp.", usr_previo.correo_corp, instance.correo_corp)
            add_cambio("Gmail", usr_previo.gmail, instance.gmail)
            if usr_previo.password_gmail != instance.password_gmail:
                add_cambio("Contraseña Gmail", "••••••••", "••••••••")


            add_cambio(
                "SIF",
                "Sí" if usr_previo.sif else "No",
                "Sí" if instance.sif else "No"
            )
            add_cambio(
                "VPN Cisco",
                "Sí" if usr_previo.vpn_cisco else "No",
                "Sí" if instance.vpn_cisco else "No"
            )
            if usr_previo.password_vpn != instance.password_vpn:
                add_cambio(
                    "Contraseña VPN",
                    "••••••••",
                    "••••••••"
                )

            add_cambio(
                "Teléfono",
                usr_previo.telefono,
                instance.telefono
            )

            add_cambio(
                "Celular",
                usr_previo.celular,
                instance.celular
            )

            add_cambio(
                "Anexo",
                usr_previo.anexo,
                instance.anexo
            )

            if cambios:
                HistorialUsuario.objects.create(
                    usuario=instance,
                    accion="MODIFICACION",
                    modificado_por=get_current_audit_username(),
                    observacion="||".join(cambios)
                )

def liberar_equipos_usuario(usuario):
    """Libera y audita cada equipo asociado dentro de una transacciÃ³n."""
    with transaction.atomic():
        equipos = Equipamiento.objects.select_for_update().filter(
            usuario=usuario
        )

        for equipo in equipos:
            equipo.usuario = None
            equipo.estado = 'STOCK'
            equipo.fecha_asignacion = None
            equipo.save(
                update_fields=[
                    'usuario',
                    'estado',
                    'fecha_asignacion',
                ]
            )


@receiver(post_save, sender=Usuario)
def auto_sync_usuario(sender, instance, created, **kwargs):

    # =====================================
    # USUARIO DADO DE BAJA
    # =====================================
    if instance.estado == 'BAJA':

        # Liberar todos sus equipos
        liberar_equipos_usuario(instance)

        # Liberar su IP y cerrar la asignación activa.
        from .services.asignacion_ips import assign_ip_to_user
        assign_ip_to_user(instance.pk, None)

        # Liberar su anexo
        anexo = Anexo.objects.filter(
            usuario=instance
        ).first()

        if anexo:
            anexo.usuario = None
            anexo.save()

        return

    # =====================================
    # SINCRONIZAR HOSTNAME
    # Usuario -> Notebook / Mac asignado
    # =====================================
    nuevo_hostname = (
        instance.hostname.strip()
        if instance.hostname
        else None
    )

    equipos_con_hostname = Equipamiento.objects.filter(
        usuario=instance,
        tipo__in=[
            'Notebook',
            'Mac'
        ]
    )

    for equipo in equipos_con_hostname:

        hostname_actual = (
            equipo.hostname.strip()
            if equipo.hostname
            else None
        )

        if hostname_actual != nuevo_hostname:
            equipo.hostname = nuevo_hostname

            equipo.save(
                update_fields=[
                    'hostname'
                ]
            )

    # =====================================
    # VINCULAR EQUIPO DISPONIBLE
    # POR HOSTNAME
    # =====================================
    if nuevo_hostname:
        with transaction.atomic():
            equipos_disponibles = Equipamiento.objects.select_for_update().filter(
                usuario__isnull=True,
                tipo__in=[
                    'Notebook',
                    'Mac'
                ],
                hostname__iexact=nuevo_hostname
            )

            for equipo in equipos_disponibles:
                equipo.usuario = instance
                equipo.estado = 'ASIGNADO'
                equipo.save(
                    update_fields=[
                        'usuario',
                        'estado',
                    ]
                )


# =========================================
# ELIMINACIÓN COMPLETA DE USUARIO
# =========================================

@receiver(pre_delete, sender=Usuario)
def liberar_recursos_al_eliminar_usuario(
    sender,
    instance,
    **kwargs
):

    # Liberar equipos
    liberar_equipos_usuario(instance)

    # Liberar IP y cerrar la asignación activa.
    from .services.asignacion_ips import assign_ip_to_user
    assign_ip_to_user(instance.pk, None)

    # Liberar anexo
    anexo = Anexo.objects.filter(
        usuario=instance
    ).first()

    if anexo:
        anexo.usuario = None
        anexo.save()
