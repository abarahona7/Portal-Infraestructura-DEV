from ipaddress import ip_address
import re
from rest_framework import serializers
from django.db import transaction
from django.db.models.functions import Lower, Trim

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
    Servidor,
    Departamento,
    SubArea,
    _normalize_key,
    _normalize_spaces,
)
from .services.asignacion_ips import (
    IP_ALLOWED_NETWORKS,
    IpAssignmentError,
    assign_ip_to_user,
    create_server_with_ip,
    update_server_with_ip,
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

    class Meta:
        model = IP
        fields = '__all__'

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
        if instance:
            try:
                server = instance.servidor
            except Servidor.DoesNotExist:
                server = None

        if server:
            if (
                'direccion_ip' in attrs
                and attrs['direccion_ip'] != instance.direccion_ip
            ):
                raise serializers.ValidationError({
                    'direccion_ip': (
                        'La dirección de una IP asignada a un servidor no se '
                        'puede modificar. Cambia la IP desde Servidores.'
                    )
                })

            if (
                'asignado_otro' in attrs
                and attrs.get('asignado_otro') != instance.asignado_otro
            ):
                raise serializers.ValidationError({
                    'asignado_otro': (
                        'La asignación de esta IP se administra desde Servidores.'
                    )
                })

        if (
            instance
            and instance.usuario_id
            and 'asignado_otro' in attrs
            and attrs.get('asignado_otro')
        ):
            raise serializers.ValidationError({
                'asignado_otro': (
                    'Esta IP está vinculada a un usuario. Para cambiar su asignación, '
                    'debe gestionarla desde el módulo Usuarios.'
                )
            })

        observacion = attrs.get('observacion')
        if isinstance(observacion, str):
            attrs['observacion'] = observacion.strip() or None

        return attrs


class ServidorSerializer(serializers.ModelSerializer):
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


class EquipamientoSerializer(serializers.ModelSerializer):
    usuario_red = serializers.ReadOnlyField(
        source='usuario.usuario_red'
    )

    usuario_nombre = serializers.ReadOnlyField(
        source='usuario.nombre_completo'
    )

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

    def get_pin_configured(self, obj):
        return bool(obj.pin)

    def get_ip_asignada(self, obj):
        if obj.tipo != 'Notebook' or not obj.usuario_id:
            return None

        try:
            return obj.usuario.ip.direccion_ip
        except IP.DoesNotExist:
            return None

    def update(self, instance, validated_data):
        for field in ('icloud_password', 'pin'):
            if validated_data.get(field) in ('', None):
                validated_data.pop(field, None)
        return super().update(instance, validated_data)

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
                cleaned = attrs[field].strip()
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

            if not af.isalnum():
                raise serializers.ValidationError({
                    "af":
                        "El Activo Fijo (AF) solo puede "
                        "contener letras y números."
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
        # =====================================
        # NÚMERO DE SERIE DUPLICADO
        # =====================================

        if (
            serie and
            Equipamiento.objects.filter(
                numero_serie__iexact=serie.strip()
            ).exclude(
                pk=getattr(instance, 'pk', None)
            ).exists()
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
            Equipamiento.objects.filter(
                af__iexact=af.strip()
            ).exclude(
                pk=getattr(instance, 'pk', None)
            ).exists()
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
            ]
        ):
            raise serializers.ValidationError({
                "usuario":
                    "No se puede asignar un equipo "
                    "a un usuario que se encuentra "
                    "de baja o en licencia."
            })

        return attrs


class UsuarioSerializer(serializers.ModelSerializer):
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
        ip_enviada = 'ip_seleccionada' in validated_data

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

        if ip_enviada and usuario.estado != 'BAJA':
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

        if instance is None and not departamento:
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

        # Una IP nueva solo puede asignarse a usuarios ACTIVOS.
        # Si el usuario está en LICENCIA se permite conservar su IP actual,
        # pero no cambiarla por otra. BAJA libera la IP mediante la señal
        # post_save y nunca debe recibir una nueva asignación.
        if 'ip_seleccionada' in attrs and attrs.get('ip_seleccionada') is not None:
            estado_resultante = attrs.get(
                'estado',
                getattr(instance, 'estado', 'ACTIVO'),
            )

            ip_solicitada = str(attrs['ip_seleccionada'])
            ip_actual = None
            if instance:
                ip_actual_obj = IP.objects.filter(usuario=instance).first()
                if ip_actual_obj:
                    ip_actual = ip_actual_obj.direccion_ip

            es_ip_actual = bool(
                instance
                and ip_actual
                and ip_actual == ip_solicitada
            )

            if estado_resultante == 'BAJA':
                raise serializers.ValidationError({
                    'ip_seleccionada': (
                        'No se puede asignar una IP a un usuario dado de baja.'
                    )
                })

            if estado_resultante == 'LICENCIA' and not es_ip_actual:
                raise serializers.ValidationError({
                    'ip_seleccionada': (
                        'No se puede asignar una IP nueva a un usuario en licencia médica.'
                    )
                })

        return attrs

class PerfilGenericoSerializer(serializers.ModelSerializer):
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

        if instance is None and not departamento:
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

    class Meta:
        model = PCGenerico
        fields = '__all__'
        read_only_fields = [
            'fecha_creacion',
            'fecha_actualizacion',
        ]

    def get_password_configured(self, obj):
        return bool(obj.password)

    def update(self, instance, validated_data):
        if validated_data.get('password') in ('', None):
            validated_data.pop('password', None)
        return super().update(instance, validated_data)

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
        value = value.strip()
        if not value:
            return None
        if len(value) > 20:
            raise serializers.ValidationError(
                'El N° de Serie permite un máximo de 20 caracteres.'
            )
        instance = getattr(self, 'instance', None)
        if PCGenerico.objects.filter(numero_serie__iexact=value).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
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

        if not value.isalnum():
            raise serializers.ValidationError(
                "El Activo Fijo solo puede contener letras y números."
            )

        instance = getattr(self, 'instance', None)
        if PCGenerico.objects.filter(activo_fijo__iexact=value).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                'Ya existe un PC Genérico con este Activo Fijo.'
            )

        return value

    def validate(self, attrs):
        if attrs.get('usuario_local'):
            attrs['usuario_local'] = (
                attrs['usuario_local'].strip()
            )

        if attrs.get('dpto_area'):
            attrs['dpto_area'] = (
                attrs['dpto_area'].strip()
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

        return attrs


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
            'ip_asignada',
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

    class Meta:
        model = PCGenerico
        fields = [
            'id', 'usuario_local', 'password_configured', 'hostname',
            'dpto_area', 'marca', 'modelo', 'numero_serie', 'activo_fijo',
            'teamviewer_id', 'observaciones', 'fecha_creacion',
            'fecha_actualizacion',
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
