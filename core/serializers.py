from ipaddress import ip_address
import re
from rest_framework import serializers
from django.db import transaction
from django.db.models.functions import Lower, Trim
from .equipment_categories import EQUIPMENT_CATEGORY_TYPES

from .models import (
    Usuario,
    Equipamiento,
    HistorialEquipo,
    HistorialUsuario,
    PerfilGenerico,
    IP,
    Anexo,
    HistorialAnexo,
    PCGenerico,
    HistorialPCGenerico,
    HistorialAsignacionIP,
    Servidor,
    HistorialServidor,
    HistorialPerfilGenerico,
    TipoAsignacionIP,
    Departamento,
    SubArea,
    _normalize_key,
    _normalize_spaces,
)
from .services.asignacion_ips import (
    IP_ALLOWED_NETWORKS,
    IpAssignmentError,
    assign_ip_to_user,
    create_pc_generico_with_ip,
    create_server_with_ip,
    update_pc_generico_with_ip,
    update_server_with_ip,
    validate_pc_generico_ip,
    validate_server_ip,
    validate_user_ip,
)


def _has_normalized_duplicate(queryset, field_name, value, exclude_pk=None):
    normalized = (_normalize_spaces(value) or '').lower()
    if not normalized:
        return False

    queryset = queryset.annotate(
        _normalized_value=Lower(Trim(field_name))
    ).filter(_normalized_value=normalized)

    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    return queryset.exists()


HOSTNAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def _validate_hostname_format(value, field_label='Hostname'):
    value = _normalize_spaces(value)
    if not value:
        return value

    if ' ' in value or not HOSTNAME_PATTERN.fullmatch(value):
        raise serializers.ValidationError(
            f'{field_label} solo puede contener letras, números, punto, guion y guion bajo, sin espacios.'
        )

    return value


def _validate_no_whitespace(value, field_label):
    value = _normalize_spaces(value)
    if not value:
        return value

    if any(char.isspace() for char in value):
        raise serializers.ValidationError(
            f'{field_label} no puede contener espacios.'
        )

    return value


class InternalModelFieldsMixin:
    """Exclude database-only normalization fields from public API schemas."""

    internal_model_fields = ()

    def get_fields(self):
        fields = super().get_fields()
        for field_name in self.internal_model_fields:
            fields.pop(field_name, None)
        return fields


class SubAreaSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.ReadOnlyField(
        source='departamento.nombre'
    )

    class Meta:
        model = SubArea
        fields = [
            'id',
            'departamento',
            'departamento_nombre',
            'nombre',
            'activo',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = [
            'fecha_creacion',
            'fecha_actualizacion',
        ]

    def validate_nombre(self, value):
        value = _normalize_spaces(value)
        if not value:
            raise serializers.ValidationError(
                'El nombre de la subárea es obligatorio.'
            )
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        departamento = attrs.get(
            'departamento',
            getattr(instance, 'departamento', None),
        )
        nombre = attrs.get(
            'nombre',
            getattr(instance, 'nombre', None),
        )

        if departamento and nombre:
            normalized = _normalize_key(nombre)
            duplicated = SubArea.objects.filter(
                departamento=departamento,
                nombre_normalizado=normalized,
            ).exclude(pk=getattr(instance, 'pk', None)).exists()

            if duplicated:
                raise serializers.ValidationError({
                    'nombre': (
                        'Ya existe una subárea con este nombre '
                        'dentro del departamento seleccionado.'
                    )
                })

        return attrs


class DepartamentoSerializer(serializers.ModelSerializer):
    subareas = SubAreaSerializer(many=True, read_only=True)

    class Meta:
        model = Departamento
        fields = [
            'id',
            'nombre',
            'activo',
            'subareas',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = [
            'fecha_creacion',
            'fecha_actualizacion',
        ]

    def validate_nombre(self, value):
        value = _normalize_spaces(value)
        if not value:
            raise serializers.ValidationError(
                'El nombre del departamento es obligatorio.'
            )

        instance = getattr(self, 'instance', None)
        if Departamento.objects.filter(
            nombre_normalizado=_normalize_key(value)
        ).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError(
                'Ya existe un departamento con este nombre.'
            )

        return value



class IPSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    usuario_nombre = serializers.ReadOnlyField(
        source='usuario.nombre_completo'
    )
    estado = serializers.CharField(read_only=True)
    tipo_asignacion = serializers.SerializerMethodField()
    asignado_a = serializers.SerializerMethodField()

    class Meta:
        model = IP
        fields = '__all__'

    def get_tipo_asignacion(self, obj):
        assignment = getattr(obj, 'asignacion_activa', None)
        return assignment.tipo if assignment else None

    def get_asignado_a(self, obj):
        assignment = getattr(obj, 'asignacion_activa', None)
        return assignment.propietario_nombre if assignment else None

    def validate_direccion_ip(self, value):
        parsed_ip = ip_address(value)

        if parsed_ip.version != 4:
            raise serializers.ValidationError(
                'Solo se permiten direcciones IPv4.'
            )

        network = next(
            (item for item in IP_ALLOWED_NETWORKS if parsed_ip in item),
            None,
        )

        if network is None:
            raise serializers.ValidationError(
                'La IP no pertenece a un segmento administrado en Gestión IPs.'
            )

        if parsed_ip in (network.network_address, network.broadcast_address):
            raise serializers.ValidationError(
                'No se puede registrar la dirección de red ni la dirección broadcast.'
            )

        return str(parsed_ip)

    def validate(self, attrs):
        # La relación IP -> Usuario se administra exclusivamente desde
        # Crear/Editar Usuario. Gestión IPs no puede crear, cambiar ni
        # quitar esa relación directamente.
        if 'usuario' in self.initial_data:
            raise serializers.ValidationError({
                'usuario': (
                    'La asignación de IP a usuarios se gestiona únicamente '
                    'desde el módulo Usuarios.'
                )
            })

        asignado_otro = attrs.get('asignado_otro')
        if isinstance(asignado_otro, str):
            attrs['asignado_otro'] = asignado_otro.strip() or None

        instance = getattr(self, 'instance', None)
        server = None
        pc_generico = None
        assignment = None
        if instance:
            assignment = getattr(instance, 'asignacion_activa', None)
            try:
                server = instance.servidor
            except Servidor.DoesNotExist:
                server = None
            try:
                pc_generico = instance.pc_generico
            except PCGenerico.DoesNotExist:
                pc_generico = None

        assignment_modules = {
            TipoAsignacionIP.USUARIO: 'Usuarios',
            TipoAsignacionIP.SERVIDOR: 'Servidores',
            TipoAsignacionIP.PC_GENERICO: 'PCs Genéricos',
        }
        assignment_module = assignment_modules.get(
            getattr(assignment, 'tipo', None)
        )
        if not assignment_module and (server or pc_generico):
            assignment_module = 'Servidores' if server else 'PCs Genéricos'

        if assignment_module:
            if (
                'direccion_ip' in attrs
                and attrs['direccion_ip'] != instance.direccion_ip
            ):
                raise serializers.ValidationError({
                    'direccion_ip': (
                        'La dirección de una IP asignada no se puede modificar. '
                        f'Cambia la IP desde {assignment_module}.'
                    )
                })

            if (
                'asignado_otro' in attrs
                and attrs.get('asignado_otro') != instance.asignado_otro
            ):
                raise serializers.ValidationError({
                    'asignado_otro': (
                        'La asignación de esta IP se administra desde '
                        f'{assignment_module}.'
                    )
                })

        observacion = attrs.get('observacion')
        if isinstance(observacion, str):
            attrs['observacion'] = observacion.strip() or None

        return attrs


class HistorialAsignacionIPSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='get_tipo_display', read_only=True)
    accion_nombre = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = HistorialAsignacionIP
        fields = [
            'id',
            'direccion_ip',
            'accion',
            'accion_nombre',
            'tipo',
            'tipo_nombre',
            'propietario_id',
            'propietario_nombre',
            'realizado_por',
            'fecha_movimiento',
        ]
        read_only_fields = fields


class HistorialServidorSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialServidor
        fields = '__all__'


class ServidorSerializer(InternalModelFieldsMixin, serializers.ModelSerializer):
    internal_model_fields = ('hostname_normalizado',)
    historial = HistorialServidorSerializer(many=True, read_only=True)
    ip = serializers.SlugRelatedField(
        slug_field='direccion_ip',
        queryset=IP.objects.all(),
        required=True,
        allow_null=False,
    )

    class Meta:
        model = Servidor
        fields = '__all__'

    def validate_ip(self, value):
        try:
            validate_server_ip(
                value,
                server_id=getattr(getattr(self, 'instance', None), 'pk', None),
            )
        except IpAssignmentError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def create(self, validated_data):
        selected_ip = validated_data.pop('ip')
        try:
            return create_server_with_ip(selected_ip.pk, validated_data)
        except IpAssignmentError as exc:
            raise serializers.ValidationError({'ip': str(exc)}) from exc

    def update(self, instance, validated_data):
        selected_ip = validated_data.pop('ip', instance.ip)

        if selected_ip is None:
            raise serializers.ValidationError({
                'ip': 'Debe seleccionar una IP disponible.'
            })

        try:
            return update_server_with_ip(
                instance.pk,
                selected_ip.pk,
                validated_data,
            )
        except IpAssignmentError as exc:
            raise serializers.ValidationError({'ip': str(exc)}) from exc

    def validate_hostname(self, value):
        value = _validate_hostname_format(value)
        if not value:
            raise serializers.ValidationError('Debe ingresar el Hostname del servidor.')

        instance = getattr(
            self,
            'instance',
            None
        )

        if Servidor.objects.filter(
            hostname__iexact=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Ya existe un servidor registrado con este Hostname."
            )

        return value

    def validate_descripcion(self, value):
        if not value:
            return value

        return value.strip()

class HistorialAnexoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialAnexo
        fields = '__all__'


class AnexoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(
        source='usuario.nombre_completo'
    )

    departamento = serializers.ReadOnlyField(
        source='usuario.dpto_area'
    )

    cargo = serializers.ReadOnlyField(
        source='usuario.cargo'
    )

    correo = serializers.ReadOnlyField(
        source='usuario.correo_corp'
    )

    historial = HistorialAnexoSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Anexo
        fields = '__all__'
        read_only_fields = [
            'estado',
            'fecha_creacion',
            'fecha_actualizacion',
        ]

    def validate_numero_anexo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Debe ingresar un número de anexo.')
        if not value.isdigit():
            raise serializers.ValidationError('El número de anexo debe contener solo números.')

        instance = getattr(self, 'instance', None)

        if Anexo.objects.filter(
            numero_anexo__iexact=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Este número de anexo ya está registrado."
            )

        return value

    def validate_usuario(self, value):
        if value is None:
            return None

        if value.estado == 'BAJA':
            raise serializers.ValidationError(
                "No se puede asignar un anexo a un usuario dado de baja."
            )

        instance = getattr(self, 'instance', None)

        if Anexo.objects.filter(
            usuario=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Este usuario ya tiene un anexo asignado."
            )

        return value



    def validate_exterior(self, value):
        if not value:
            return value

        value = value.strip()

        if (
            len(value) != 12 or
            not value.startswith('+') or
            not value[1:].isdigit()
        ):
            raise serializers.ValidationError(
                "El número exterior debe comenzar "
                "con + y contener exactamente 11 números. "
                "Ejemplo: +56254698789."
            )

        return value

class HistorialUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialUsuario
        fields = '__all__'


class HistorialEquipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEquipo
        fields = '__all__'


class EquipamientoSerializer(InternalModelFieldsMixin, serializers.ModelSerializer):
    internal_model_fields = (
        'numero_serie_normalizado',
        'hostname_computador_normalizado',
        'af_normalizado',
    )
    usuario_red = serializers.ReadOnlyField(
        source='usuario.usuario_red'
    )

    usuario_nombre = serializers.ReadOnlyField(
        source='usuario.nombre_completo'
    )

    departamento_nombre = serializers.SerializerMethodField()

    historial = HistorialEquipoSerializer(
        many=True,
        read_only=True
    )

    icloud_password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    pin = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    icloud_password_configured = serializers.SerializerMethodField()
    pin_configured = serializers.SerializerMethodField()
    ip_asignada = serializers.SerializerMethodField()

    class Meta:
        model = Equipamiento
        fields = '__all__'

    def get_icloud_password_configured(self, obj):
        return bool(obj.icloud_password)

    def get_departamento_nombre(self, obj):
        return obj.usuario.departamento.nombre if obj.usuario_id else None

    def get_pin_configured(self, obj):
        return bool(obj.pin)

    def get_ip_asignada(self, obj):
        if obj.tipo != 'Notebook' or not obj.usuario_id:
            return None

        try:
            return obj.usuario.ip.direccion_ip
        except IP.DoesNotExist:
            return None

    @transaction.atomic
    def update(self, instance, validated_data):
        old_number = instance.numero_telefono
        old_owner_id = instance.usuario_id
        next_owner = validated_data.get('usuario', instance.usuario)
        next_type = validated_data.get('tipo', instance.tipo)
        next_number = validated_data.get('numero_telefono', old_number)
        linked_user = None
        if (
            instance.tipo == next_type == 'Celular'
            and old_owner_id
            and getattr(next_owner, 'pk', None) == old_owner_id
            and old_number
            and next_number != old_number
        ):
            linked_user = Usuario.objects.select_for_update().filter(
                pk=old_owner_id, celular=old_number
            ).first()

        for field in ('icloud_password', 'pin'):
            if validated_data.get(field) in ('', None):
                validated_data.pop(field, None)
        equipo = super().update(instance, validated_data)

        # La línea del usuario es independiente cuando difiere de la del equipo.
        # Si ambas eran iguales, mantenerlas iguales al editar el celular.
        if linked_user and not Equipamiento.objects.filter(
            usuario_id=old_owner_id,
            tipo='Celular',
            numero_telefono=old_number,
        ).exclude(pk=equipo.pk).exists():
            linked_user.celular = equipo.numero_telefono or None
            linked_user.save(update_fields=['celular'])

        return equipo

    def validate(self, attrs):
        instance = getattr(
            self,
            'instance',
            None
        )

        serie = attrs.get('numero_serie')
        af = attrs.get('af')

        tipo = attrs.get(
            'tipo',
            getattr(instance, 'tipo', None)
        )

        request = self.context.get('request')
        category = request.query_params.get('categoria', '').strip() if request else ''
        if category and tipo not in EQUIPMENT_CATEGORY_TYPES.get(category, ()):
            raise serializers.ValidationError({
                'tipo': 'El tipo de equipo no corresponde a la categoría seleccionada.'
            })

        usuario = attrs.get(
            'usuario',
            getattr(instance, 'usuario', None)
        )

        hostname = attrs.get(
            'hostname',
            getattr(instance, 'hostname', None)
        )

        numero_telefono = attrs.get(
            'numero_telefono',
            getattr(instance, 'numero_telefono', None)
        )

        for field in ('marca', 'modelo', 'numero_serie', 'hostname', 'af', 'accesorios', 'imei', 'icloud_cuenta'):
            if field in attrs and isinstance(attrs[field], str):
                cleaned = (
                    _normalize_spaces(attrs[field])
                    if field in ('numero_serie', 'af')
                    else attrs[field].strip()
                )
                attrs[field] = cleaned or None

        if attrs.get('icloud_cuenta'):
            attrs['icloud_cuenta'] = attrs['icloud_cuenta'].lower()

        if 'numero_serie' in attrs:
            serie = attrs.get('numero_serie')
        if 'af' in attrs:
            af = attrs.get('af')
        if 'hostname' in attrs:
            hostname = attrs.get('hostname')

        marca_resultante = attrs.get('marca', getattr(instance, 'marca', None))
        modelo_resultante = attrs.get('modelo', getattr(instance, 'modelo', None))
        if not marca_resultante:
            raise serializers.ValidationError({'marca': 'Debe ingresar la Marca del equipo.'})
        if not modelo_resultante:
            raise serializers.ValidationError({'modelo': 'Debe ingresar el Modelo del equipo.'})

        if serie and len(serie) > 20:
            raise serializers.ValidationError({
                'numero_serie': 'El N° de Serie permite un máximo de 20 caracteres.'
            })

        if hostname:
            try:
                attrs['hostname'] = _validate_hostname_format(hostname)
                hostname = attrs['hostname']
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'hostname': exc.detail}) from exc

        # =====================================
        # VALIDAR FORMATO ACTIVO FIJO
        # =====================================

        if af:
            af = af.strip()

            if len(af) > 12:
                raise serializers.ValidationError({
                    "af":
                        "El Activo Fijo (AF) permite "
                        "un máximo de 12 caracteres."
                })

            if not re.fullmatch(r'[0-9]+', af):
                raise serializers.ValidationError({
                    "af":
                        "El Activo Fijo (AF) solo puede "
                        "contener números."
                })

            attrs['af'] = af

        # =====================================
        # VALIDAR NÚMERO TELEFÓNICO
        # =====================================

        if numero_telefono:
            numero_telefono = numero_telefono.strip()

            if (
                len(numero_telefono) != 12 or
                not numero_telefono.startswith('+') or
                not numero_telefono[1:].isdigit()
            ):
                raise serializers.ValidationError({
                    "numero_telefono":
                        "El número telefónico debe comenzar "
                        "con + y contener exactamente 11 números. "
                        "Ejemplo: +56912345678."
                })

            attrs['numero_telefono'] = numero_telefono
            line_changed = (
                instance is None
                or numero_telefono != getattr(instance, 'numero_telefono', None)
                or getattr(usuario, 'pk', None) != getattr(instance, 'usuario_id', None)
            )
            if tipo not in {'Celular', 'Tablet', 'BAM / Router'} and (
                instance is None or line_changed or tipo != instance.tipo
            ):
                raise serializers.ValidationError({
                    'numero_telefono': 'Este tipo de equipo no utiliza línea móvil.'
                })
            if line_changed and usuario:
                other_user_has_line = Usuario.objects.filter(
                    celular=numero_telefono
                ).exclude(pk=usuario.pk).exists()
                other_owner_has_line = Equipamiento.objects.filter(
                    numero_telefono=numero_telefono,
                    usuario__isnull=False,
                ).exclude(pk=getattr(instance, 'pk', None)).exclude(
                    usuario_id=usuario.pk
                ).exists()
                if other_user_has_line or other_owner_has_line:
                    raise serializers.ValidationError({
                        'numero_telefono': 'Esta línea móvil ya está asignada a otro usuario.'
                    })
        elif 'numero_telefono' in attrs:
            attrs['numero_telefono'] = None
        # =====================================
        # NÚMERO DE SERIE DUPLICADO
        # =====================================

        if (
            serie and
            _has_normalized_duplicate(
                Equipamiento.objects.all(),
                'numero_serie',
                serie,
                getattr(instance, 'pk', None),
            )
        ):
            raise serializers.ValidationError({
                "numero_serie":
                    "Ya existe un equipo registrado "
                    "con este N° de Serie."
            })

        # =====================================
        # ACTIVO FIJO DUPLICADO
        # =====================================

        if (
            af and
            _has_normalized_duplicate(
                Equipamiento.objects.all(),
                'af',
                af,
                getattr(instance, 'pk', None),
            )
        ):
            raise serializers.ValidationError({
                "af":
                    "Ya existe un equipo registrado "
                    "con este Activo Fijo (AF)."
            })

        # =====================================
        # HOSTNAME ÚNICO NOTEBOOK / MAC
        # =====================================

        if tipo in ['Notebook', 'Mac']:

            # Si tiene usuario asignado,
            # Usuario.hostname es la fuente de verdad
            if usuario and usuario.hostname:
                hostname = usuario.hostname

            if hostname:
                hostname = hostname.strip()

                if (
                    Equipamiento.objects.filter(
                        tipo__in=['Notebook', 'Mac'],
                        hostname__iexact=hostname
                    ).exclude(
                        pk=getattr(instance, 'pk', None)
                    ).exists()
                ):
                    raise serializers.ValidationError({
                        "hostname":
                            "Ya existe un Notebook o Mac "
                            "registrado con este Hostname."
                    })

        # =====================================
        # ESTADO DEL USUARIO
        # =====================================

        if (
            usuario and
            usuario.estado in [
                'BAJA',
                'LICENCIA'
            ] and (
                instance is None
                or instance.usuario_id != usuario.pk
                or usuario.estado == 'BAJA'
            )
        ):
            raise serializers.ValidationError({
                "usuario":
                    "No se puede asignar un equipo "
                    "a un usuario que se encuentra "
                    "de baja o en licencia."
            })

        return attrs


class UsuarioSerializer(InternalModelFieldsMixin, serializers.ModelSerializer):
    internal_model_fields = (
        'nombre_completo_normalizado',
        'usuario_red_normalizado',
        'correo_corp_normalizado',
    )
    equipos = EquipamientoSerializer(many=True, read_only=True)
    historial = HistorialUsuarioSerializer(many=True, read_only=True)
    departamento_nombre = serializers.ReadOnlyField(
        source='departamento.nombre'
    )
    subarea_nombre = serializers.ReadOnlyField(
        source='subarea.nombre'
    )

    ip_actual = serializers.SerializerMethodField()

    anexo_actual = serializers.SerializerMethodField()

    ip_seleccionada = serializers.IPAddressField(
        write_only=True,
        required=False,
        allow_null=True
    )

    password_gmail = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    password_gmail_configured = serializers.SerializerMethodField()

    password_vpn = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    password_vpn_configured = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = '__all__'

    def get_ip_actual(self, obj):
        try:
            return obj.ip.direccion_ip
        except IP.DoesNotExist:
            return None
        
    def get_anexo_actual(self, obj):
        try:
            anexo = obj.anexo_asignado

            return {
                'id': anexo.id,
                'numero_anexo': anexo.numero_anexo,
                'exterior': anexo.exterior,
                'estado': anexo.estado,
            }

        except Anexo.DoesNotExist:
            return None
        
    def validate_nombre_completo(self, value):
        value = _normalize_spaces(value)
        if not value:
            raise serializers.ValidationError('Debe ingresar el Nombre Completo.')
        return value

    def validate_usuario_red(self, value):
        value = _validate_no_whitespace(value, 'El Usuario de Red')
        if not value:
            raise serializers.ValidationError('Debe ingresar el Usuario de Red.')
        return value.lower()

    def validate_hostname(self, value):
        if not value:
            return value
        value = _validate_hostname_format(value)
        instance = getattr(self, 'instance', None)
        if Usuario.objects.filter(hostname__iexact=value).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario registrado con este Hostname.'
            )
        return value

    def validate_celular(self, value):
        value = _normalize_spaces(value)
        if not value:
            return None
        if not re.fullmatch(r'\+[0-9]{11}', value):
            raise serializers.ValidationError(
                'La línea móvil debe tener el formato +56912345678.'
            )

        instance = getattr(self, 'instance', None)
        if Usuario.objects.filter(celular=value).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                'Esta línea móvil ya está registrada en otro usuario.'
            )
        if Equipamiento.objects.filter(
            numero_telefono=value,
            usuario__isnull=False,
        ).exclude(usuario_id=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError(
                'Esta línea móvil figura en un equipo asignado a otro usuario.'
            )
        return value

    def validate_ip_seleccionada(self, value):
        if value is None:
            return None

        try:
            ip = IP.objects.get(direccion_ip=value)
        except IP.DoesNotExist:
            raise serializers.ValidationError(
                "La IP seleccionada no existe en Gestión de IPs."
            )

        try:
            validate_user_ip(
                ip,
                user_id=getattr(getattr(self, 'instance', None), 'pk', None),
            )
        except IpAssignmentError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        return value

    @transaction.atomic
    def create(self, validated_data):
        ip_seleccionada = validated_data.pop(
            'ip_seleccionada',
            None
        )

        usuario = super().create(validated_data)

        if ip_seleccionada is not None:
            try:
                assign_ip_to_user(usuario.pk, ip_seleccionada)
            except IpAssignmentError as exc:
                raise serializers.ValidationError({
                    'ip_seleccionada': str(exc),
                }) from exc

        return usuario

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'celular' in validated_data:
            instance = Usuario.objects.select_for_update().get(pk=instance.pk)
        ip_enviada = 'ip_seleccionada' in validated_data

        # Una línea puede estar registrada solo en el celular asignado (datos
        # anteriores a la línea independiente del usuario). Al editarla desde
        # Usuarios, actualizar el mismo celular sin tocar otras líneas.
        equipos_de_la_linea = []
        if 'celular' in validated_data and validated_data.get('estado', instance.estado) != 'BAJA':
            celulares = list(
                Equipamiento.objects.select_for_update().filter(
                    usuario=instance, tipo='Celular'
                )
            )
            linea_anterior = instance.celular
            if not linea_anterior:
                lineas = {equipo.numero_telefono for equipo in celulares if equipo.numero_telefono}
                linea_anterior = next(iter(lineas)) if len(lineas) == 1 else None
            if linea_anterior:
                equipos_de_la_linea = [
                    equipo for equipo in celulares
                    if equipo.numero_telefono == linea_anterior
                ]

        ip_seleccionada = validated_data.pop(
        'ip_seleccionada',
        None
    )

        for field in ('password_gmail', 'password_vpn'):
            if validated_data.get(field) in ('', None):
                validated_data.pop(field, None)

        usuario = super().update(
        instance,
        validated_data
        )

        for equipo in equipos_de_la_linea:
            if equipo.numero_telefono != usuario.celular:
                equipo.numero_telefono = usuario.celular
                equipo.save(update_fields=['numero_telefono'])

        if equipos_de_la_linea:
            usuario._prefetched_objects_cache = {}

        if ip_enviada and usuario.estado not in {'BAJA', 'LICENCIA'}:
            try:
                assign_ip_to_user(usuario.pk, ip_seleccionada)
            except IpAssignmentError as exc:
                raise serializers.ValidationError({
                    'ip_seleccionada': str(exc),
                }) from exc

        return usuario

    def get_password_gmail_configured(self, obj):
        return bool(obj.password_gmail)

    def get_password_vpn_configured(self, obj):
        return bool(obj.password_vpn)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        for field in (
            'nombre_completo',
            'usuario_red',
            'correo_corp',
            'dpto_area',
            'cargo',
            'hostname',
            'gmail',
            'celular',
            'telefono',
            'anexo',
        ):
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = _normalize_spaces(attrs[field])

        if attrs.get('usuario_red'):
            attrs['usuario_red'] = attrs['usuario_red'].lower()
        if attrs.get('correo_corp'):
            attrs['correo_corp'] = attrs['correo_corp'].lower()
        if attrs.get('gmail'):
            attrs['gmail'] = attrs['gmail'].lower()

        nombre = attrs.get('nombre_completo')
        user_red = attrs.get('usuario_red')
        correo = attrs.get('correo_corp')

        if nombre and _has_normalized_duplicate(
            Usuario.objects.all(),
            'nombre_completo',
            nombre,
            getattr(instance, 'pk', None),
        ):
            raise serializers.ValidationError({
                'nombre_completo':
                'Ya existe un usuario registrado con este Nombre Completo.'
            })

        if user_red and _has_normalized_duplicate(
            Usuario.objects.all(),
            'usuario_red',
            user_red,
            getattr(instance, 'pk', None),
        ):
            raise serializers.ValidationError({
                'usuario_red':
                'Ya existe un usuario con este Usuario de Red.'
            })

        if correo and _has_normalized_duplicate(
            Usuario.objects.all(),
            'correo_corp',
            correo,
            getattr(instance, 'pk', None),
        ):
            raise serializers.ValidationError({
                'correo_corp':
                'Ya existe un usuario con este Correo Corporativo.'
            })

        departamento = attrs.get(
            'departamento',
            getattr(instance, 'departamento', None),
        )
        subarea = attrs.get(
            'subarea',
            getattr(instance, 'subarea', None),
        )

        if not departamento:
            raise serializers.ValidationError({
                'departamento': 'Debe seleccionar un Departamento.'
            })

        if subarea and not departamento:
            raise serializers.ValidationError({
                'departamento':
                'Debe seleccionar el departamento de la subárea indicada.'
            })

        if (
            departamento
            and subarea
            and subarea.departamento_id != departamento.id
        ):
            raise serializers.ValidationError({
                'subarea':
                'La subárea seleccionada no pertenece al departamento indicado.'
            })

        if departamento and not departamento.activo:
            current_id = getattr(
                getattr(instance, 'departamento', None),
                'id',
                None,
            )
            if departamento.id != current_id:
                raise serializers.ValidationError({
                    'departamento':
                    'No se puede asignar un departamento inactivo.'
                })

        if subarea and not subarea.activo:
            current_id = getattr(
                getattr(instance, 'subarea', None),
                'id',
                None,
            )
            if subarea.id != current_id:
                raise serializers.ValidationError({
                    'subarea':
                    'No se puede asignar una subárea inactiva.'
                })

        if departamento:
            attrs['dpto_area'] = departamento.nombre

        # Una IP solo puede asignarse a usuarios ACTIVOS. Tanto BAJA como
        # LICENCIA liberan la IP mediante la señal post_save.
        if 'ip_seleccionada' in attrs and attrs.get('ip_seleccionada') is not None:
            estado_resultante = attrs.get(
                'estado',
                getattr(instance, 'estado', 'ACTIVO'),
            )

            if estado_resultante == 'BAJA':
                raise serializers.ValidationError({
                    'ip_seleccionada': (
                        'No se puede asignar una IP a un usuario dado de baja.'
                    )
                })

            if estado_resultante == 'LICENCIA':
                raise serializers.ValidationError({
                    'ip_seleccionada': (
                        'Los usuarios en licencia médica no pueden conservar ni recibir una IP.'
                    )
                })

        return attrs

class HistorialPerfilGenericoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPerfilGenerico
        fields = '__all__'


class PerfilGenericoSerializer(InternalModelFieldsMixin, serializers.ModelSerializer):
    internal_model_fields = ('usuario_normalizado',)
    historial = HistorialPerfilGenericoSerializer(many=True, read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    password_configured = serializers.SerializerMethodField()
    departamento_nombre = serializers.ReadOnlyField(
        source='departamento.nombre'
    )
    subarea_nombre = serializers.ReadOnlyField(
        source='subarea.nombre'
    )

    class Meta:
        model = PerfilGenerico
        fields = '__all__'

    def get_password_configured(self, obj):
        return bool(obj.password)

    def update(self, instance, validated_data):
        if validated_data.get('password') in ('', None):
            validated_data.pop('password', None)
        return super().update(instance, validated_data)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        for field in ('nombre', 'usuario', 'correo', 'dpto_area', 'observaciones'):
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = _normalize_spaces(attrs[field])

        if attrs.get('correo'):
            attrs['correo'] = attrs['correo'].lower()

        nombre = attrs.get('nombre', getattr(instance, 'nombre', None))
        usuario_resultante = attrs.get('usuario', getattr(instance, 'usuario', None))
        tipo = attrs.get('tipo', getattr(instance, 'tipo', 'On Premise'))

        if not nombre:
            raise serializers.ValidationError({
                'nombre': 'Debe ingresar el Nombre / Perfil.'
            })
        if not usuario_resultante:
            raise serializers.ValidationError({
                'usuario': 'Debe ingresar el Usuario del Perfil Genérico.'
            })
        try:
            attrs['usuario'] = _validate_no_whitespace(usuario_resultante, 'El Usuario del Perfil Genérico')
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'usuario': exc.detail}) from exc

        if tipo not in ('On Premise', 'O365'):
            raise serializers.ValidationError({
                'tipo': 'Tipo de cuenta inválido. Use On Premise u O365.'
            })

        usuario = attrs.get('usuario')
        if usuario and PerfilGenerico.objects.filter(
            usuario__iexact=usuario.strip()
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError({
                'usuario':
                'Ya existe un Perfil Genérico registrado con este Usuario.'
            })

        departamento = attrs.get(
            'departamento',
            getattr(instance, 'departamento', None),
        )
        subarea = attrs.get(
            'subarea',
            getattr(instance, 'subarea', None),
        )

        if not departamento:
            raise serializers.ValidationError({
                'departamento': 'Debe seleccionar un Departamento.'
            })

        if subarea and not departamento:
            raise serializers.ValidationError({
                'departamento': (
                    'Debe seleccionar el Departamento correspondiente a la Subárea.'
                )
            })

        if subarea and departamento:
            if subarea.departamento_id != departamento.id:
                raise serializers.ValidationError({
                    'subarea': (
                        'La Subárea seleccionada no pertenece al Departamento indicado.'
                    )
                })

        if departamento and not departamento.activo:
            current_id = getattr(getattr(instance, 'departamento', None), 'id', None)
            if departamento.id != current_id:
                raise serializers.ValidationError({
                    'departamento': 'No se puede asignar un Departamento inactivo.'
                })

        if subarea and not subarea.activo:
            current_id = getattr(getattr(instance, 'subarea', None), 'id', None)
            if subarea.id != current_id:
                raise serializers.ValidationError({
                    'subarea': 'No se puede asignar una Subárea inactiva.'
                })

        return attrs


class HistorialPCGenericoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPCGenerico
        fields = '__all__'


class PCGenericoSerializer(serializers.ModelSerializer):
    historial = HistorialPCGenericoSerializer(
        many=True,
        read_only=True
    )

    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    password_configured = serializers.SerializerMethodField()
    ip_actual = serializers.SerializerMethodField()
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')
    ip_seleccionada = serializers.IPAddressField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = PCGenerico
        fields = [
            'id', 'usuario_local', 'password', 'password_configured',
            'hostname', 'dpto_area', 'departamento', 'departamento_nombre',
            'subarea', 'subarea_nombre', 'marca', 'modelo', 'numero_serie',
            'activo_fijo', 'teamviewer_id', 'observaciones', 'ip_actual',
            'ip_seleccionada', 'fecha_creacion', 'fecha_actualizacion',
            'historial',
        ]
        read_only_fields = [
            'fecha_creacion',
            'fecha_actualizacion',
            'dpto_area',
        ]

    def get_password_configured(self, obj):
        return bool(obj.password)

    def get_ip_actual(self, obj):
        return obj.ip.direccion_ip if obj.ip_id else None

    def validate_usuario_local(self, value):
        value = _normalize_spaces(value)
        if not value:
            raise serializers.ValidationError('Debe ingresar el Usuario Local.')
        return value

    def validate_hostname(self, value):
        value = _validate_hostname_format(value)
        if not value:
            raise serializers.ValidationError('Debe ingresar el Hostname del PC Genérico.')

        instance = getattr(self, 'instance', None)
        if PCGenerico.objects.filter(
            hostname__iexact=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Ya existe un PC Genérico con este Hostname."
            )

        return value

    def validate_numero_serie(self, value):
        if not value:
            return None
        value = _normalize_spaces(value)
        if not value:
            return None
        if len(value) > 20:
            raise serializers.ValidationError(
                'El N° de Serie permite un máximo de 20 caracteres.'
            )
        instance = getattr(self, 'instance', None)
        if _has_normalized_duplicate(
            PCGenerico.objects.all(),
            'numero_serie',
            value,
            getattr(instance, 'pk', None),
        ):
            raise serializers.ValidationError(
                'Ya existe un PC Genérico con este N° de Serie.'
            )
        return value

    def validate_activo_fijo(self, value):
        if not value:
            return None

        value = value.strip()
        if not value:
            return None

        if len(value) > 12:
            raise serializers.ValidationError(
                "El Activo Fijo permite un máximo de 12 caracteres."
            )

        if not re.fullmatch(r'[0-9]+', value):
            raise serializers.ValidationError(
                "El Activo Fijo solo puede contener números."
            )

        instance = getattr(self, 'instance', None)
        if PCGenerico.objects.filter(activo_fijo__iexact=value).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                'Ya existe un PC Genérico con este Activo Fijo.'
            )

        return value

    def validate_ip_seleccionada(self, value):
        if value is None:
            return None

        try:
            ip = IP.objects.get(direccion_ip=value)
            validate_pc_generico_ip(
                ip,
                pc_id=getattr(getattr(self, 'instance', None), 'pk', None),
            )
        except IP.DoesNotExist as exc:
            raise serializers.ValidationError(
                'La IP seleccionada ya no existe.'
            ) from exc
        except IpAssignmentError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        return value

    def validate(self, attrs):
        if attrs.get('usuario_local'):
            attrs['usuario_local'] = (
                attrs['usuario_local'].strip()
            )

        if attrs.get('marca'):
            attrs['marca'] = attrs['marca'].strip()

        if attrs.get('modelo'):
            attrs['modelo'] = attrs['modelo'].strip()

        if 'numero_serie' in attrs and isinstance(attrs.get('numero_serie'), str):
            attrs['numero_serie'] = attrs['numero_serie'].strip() or None

        if attrs.get('teamviewer_id'):
            attrs['teamviewer_id'] = attrs['teamviewer_id'].strip()

        if attrs.get('observaciones'):
            attrs['observaciones'] = (
                attrs['observaciones'].strip()
            )

        instance = getattr(self, 'instance', None)
        departamento = attrs.get(
            'departamento',
            getattr(instance, 'departamento', None),
        )
        subarea = attrs.get(
            'subarea',
            getattr(instance, 'subarea', None),
        )

        if not departamento:
            raise serializers.ValidationError({
                'departamento': 'Debe seleccionar un Departamento.'
            })
        if subarea and not departamento:
            raise serializers.ValidationError({
                'departamento': (
                    'Debe seleccionar el Departamento correspondiente a la Subárea.'
                )
            })
        if subarea and departamento:
            if subarea.departamento_id != departamento.id:
                raise serializers.ValidationError({
                    'subarea': (
                        'La Subárea seleccionada no pertenece al Departamento indicado.'
                    )
                })
        if departamento and not departamento.activo:
            current_id = getattr(
                getattr(instance, 'departamento', None),
                'id',
                None,
            )
            if departamento.id != current_id:
                raise serializers.ValidationError({
                    'departamento': 'No se puede asignar un Departamento inactivo.'
                })
        if subarea and not subarea.activo:
            current_id = getattr(
                getattr(instance, 'subarea', None),
                'id',
                None,
            )
            if subarea.id != current_id:
                raise serializers.ValidationError({
                    'subarea': 'No se puede asignar una Subárea inactiva.'
                })

        return attrs

    def create(self, validated_data):
        selected_ip = validated_data.pop('ip_seleccionada', None)
        try:
            return create_pc_generico_with_ip(selected_ip, validated_data)
        except IpAssignmentError as exc:
            raise serializers.ValidationError({
                'ip_seleccionada': str(exc),
            }) from exc

    def update(self, instance, validated_data):
        if validated_data.get('password') in ('', None):
            validated_data.pop('password', None)

        if 'ip_seleccionada' in validated_data:
            selected_ip = validated_data.pop('ip_seleccionada')
        else:
            selected_ip = instance.ip.direccion_ip if instance.ip_id else None

        try:
            return update_pc_generico_with_ip(
                instance.pk,
                selected_ip,
                validated_data,
            )
        except IpAssignmentError as exc:
            raise serializers.ValidationError({
                'ip_seleccionada': str(exc),
            }) from exc


# =========================================
# SERIALIZADORES OPTIMIZADOS DE LISTADO / REFERENCIA
# =========================================

class EquipamientoListSerializer(serializers.ModelSerializer):
    usuario_red = serializers.ReadOnlyField(source='usuario.usuario_red')
    usuario_nombre = serializers.ReadOnlyField(source='usuario.nombre_completo')
    icloud_password_configured = serializers.SerializerMethodField()
    pin_configured = serializers.SerializerMethodField()
    ip_asignada = serializers.SerializerMethodField()

    class Meta:
        model = Equipamiento
        fields = [
            'id', 'usuario', 'usuario_red', 'usuario_nombre', 'tipo', 'marca',
            'modelo', 'numero_serie', 'hostname', 'af', 'accesorios',
            'fecha_asignacion', 'estado', 'numero_telefono', 'imei',
            'icloud_cuenta', 'icloud_password_configured', 'pin_configured',
            'ip_asignada', 'token_qr',
        ]

    def get_icloud_password_configured(self, obj):
        return bool(obj.icloud_password)

    def get_pin_configured(self, obj):
        return bool(obj.pin)

    def get_ip_asignada(self, obj):
        if obj.tipo != 'Notebook' or not obj.usuario_id:
            return None
        try:
            return obj.usuario.ip.direccion_ip
        except IP.DoesNotExist:
            return None


class UsuarioListSerializer(serializers.ModelSerializer):
    equipos = EquipamientoListSerializer(many=True, read_only=True)
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')
    ip_actual = serializers.SerializerMethodField()
    anexo_actual = serializers.SerializerMethodField()
    password_gmail_configured = serializers.SerializerMethodField()
    password_vpn_configured = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre_completo', 'usuario_red', 'correo_corp', 'dpto_area',
            'departamento', 'departamento_nombre', 'subarea', 'subarea_nombre',
            'cargo', 'hostname', 'estado', 'gmail', 'celular', 'telefono',
            'anexo', 'sif', 'vpn_cisco', 'equipos', 'ip_actual', 'anexo_actual',
            'password_gmail_configured', 'password_vpn_configured',
        ]

    def get_ip_actual(self, obj):
        try:
            return obj.ip.direccion_ip
        except IP.DoesNotExist:
            return None

    def get_anexo_actual(self, obj):
        try:
            anexo = obj.anexo_asignado
        except Anexo.DoesNotExist:
            return None
        return {
            'id': anexo.id,
            'numero_anexo': anexo.numero_anexo,
            'exterior': anexo.exterior,
            'estado': anexo.estado,
        }

    def get_password_gmail_configured(self, obj):
        return bool(obj.password_gmail)

    def get_password_vpn_configured(self, obj):
        return bool(obj.password_vpn)


class AnexoListSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.nombre_completo')
    departamento = serializers.ReadOnlyField(source='usuario.dpto_area')
    cargo = serializers.ReadOnlyField(source='usuario.cargo')
    correo = serializers.ReadOnlyField(source='usuario.correo_corp')

    class Meta:
        model = Anexo
        fields = [
            'id', 'numero_anexo', 'exterior', 'usuario', 'usuario_nombre',
            'departamento', 'cargo', 'correo', 'estado', 'observaciones',
            'fecha_creacion', 'fecha_actualizacion',
        ]


class PCGenericoListSerializer(serializers.ModelSerializer):
    password_configured = serializers.SerializerMethodField()
    ip_actual = serializers.SerializerMethodField()
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')

    class Meta:
        model = PCGenerico
        fields = [
            'id', 'usuario_local', 'password_configured', 'hostname',
            'dpto_area', 'departamento', 'departamento_nombre', 'subarea',
            'subarea_nombre', 'marca', 'modelo', 'numero_serie', 'activo_fijo',
            'teamviewer_id', 'observaciones', 'fecha_creacion',
            'fecha_actualizacion', 'ip_actual',
        ]

    def get_password_configured(self, obj):
        return bool(obj.password)

    def get_ip_actual(self, obj):
        return obj.ip.direccion_ip if obj.ip_id else None


class ServidorListSerializer(serializers.ModelSerializer):
    ip = serializers.SlugRelatedField(
        slug_field='direccion_ip',
        read_only=True,
    )

    class Meta:
        model = Servidor
        fields = ['id', 'ip', 'hostname', 'descripcion']


class PerfilGenericoListSerializer(serializers.ModelSerializer):
    password_configured = serializers.SerializerMethodField()
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')

    class Meta:
        model = PerfilGenerico
        fields = [
            'id', 'nombre', 'usuario', 'password_configured', 'correo',
            'dpto_area', 'departamento', 'departamento_nombre', 'subarea',
            'subarea_nombre', 'tipo', 'estado', 'observaciones',
        ]

    def get_password_configured(self, obj):
        return bool(obj.password)


class UsuarioReferenceSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre_completo', 'usuario_red', 'estado', 'hostname',
            'dpto_area', 'departamento', 'departamento_nombre', 'subarea',
            'subarea_nombre',
        ]


class IPReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IP
        fields = ['id', 'direccion_ip', 'estado', 'observacion']


class PerfilGenericoReferenceSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.ReadOnlyField(source='departamento.nombre')
    subarea_nombre = serializers.ReadOnlyField(source='subarea.nombre')

    class Meta:
        model = PerfilGenerico
        fields = [
            'id', 'dpto_area', 'departamento', 'departamento_nombre',
            'subarea', 'subarea_nombre', 'estado',
        ]
