from rest_framework import serializers
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
    usuario_nombre = serializers.ReadOnlyField(
        source='usuario.nombre_completo'
    )

    class Meta:
        model = IP
        fields = '__all__'

    def validate(self, attrs):
        usuario = attrs.get('usuario')

        # =====================================
        # VALIDAR ESTADO DEL USUARIO
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
                    "No se puede asignar una IP "
                    "a un usuario que se encuentra "
                    "de baja o en licencia."
            })

        return attrs


class ServidorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Servidor
        fields = '__all__'

    def validate_ip(self, value):
        instance = getattr(
            self,
            'instance',
            None
        )

        if Servidor.objects.filter(
            ip=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Ya existe un servidor registrado con esta IP."
            )

        return value

    def validate_hostname(self, value):
        value = value.strip()

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

    class Meta:
        model = Equipamiento
        fields = '__all__'

    def get_icloud_password_configured(self, obj):
        return bool(obj.icloud_password)

    def get_pin_configured(self, obj):
        return bool(obj.pin)

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
        
    def validate_ip_seleccionada(self, value):
        if value is None:
            return None

        try:
            ip = IP.objects.get(direccion_ip=value)
        except IP.DoesNotExist:
            raise serializers.ValidationError(
                "La IP seleccionada no existe en Gestión de IPs."
            )

        # Permitirla si ya pertenece al mismo usuario
        if ip.usuario:
            if not self.instance or ip.usuario_id != self.instance.id:
                raise serializers.ValidationError(
                    "Esta IP ya está asignada a otro usuario."
                )

        if ip.asignado_otro:
            raise serializers.ValidationError(
                "Esta IP está reservada para otro dispositivo o servicio."
            )

        return value

    def _asignar_ip(self, usuario, direccion_ip):
        IP.objects.filter(
        usuario=usuario
    ).exclude(
        direccion_ip=direccion_ip
    ).update(
        usuario=None,
        estado='LIBRE'
    )

        IP.objects.filter(
            direccion_ip=direccion_ip
        ).update(
            usuario=usuario,
            estado='RESERVADA',
            asignado_otro=None
        )

    def create(self, validated_data):
        ip_seleccionada = validated_data.pop(
            'ip_seleccionada',
            None
        )

        usuario = super().create(validated_data)

        if ip_seleccionada is not None:
            self._asignar_ip(
                usuario,
                ip_seleccionada
            )

        return usuario

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

        if ip_enviada:
            self._asignar_ip(
            usuario,
            ip_seleccionada
        )

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

        return attrs

class PerfilGenericoSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    password_configured = serializers.SerializerMethodField()

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
        usuario = attrs.get('usuario')

        if usuario and PerfilGenerico.objects.filter(
            usuario__iexact=usuario.strip()
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError({
                "usuario":
                "Ya existe un Perfil Genérico registrado con este Usuario."
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

    def validate_hostname(self, value):
        value = value.strip()

        instance = getattr(
            self,
            'instance',
            None
        )

        if PCGenerico.objects.filter(
            hostname__iexact=value
        ).exclude(
            pk=getattr(instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError(
                "Ya existe un PC Genérico con este Hostname."
            )

        return value

    def validate_activo_fijo(self, value):
        if not value:
            return value

        value = value.strip()

        if len(value) > 12:
            raise serializers.ValidationError(
                "El Activo Fijo permite un máximo de 12 caracteres."
            )

        if not value.isalnum():
            raise serializers.ValidationError(
                "El Activo Fijo solo puede contener letras y números."
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

        if attrs.get('numero_serie'):
            attrs['numero_serie'] = (
                attrs['numero_serie'].strip()
            )

        if attrs.get('teamviewer_id'):
            attrs['teamviewer_id'] = (
                attrs['teamviewer_id'].strip()
            )

        if attrs.get('observaciones'):
            attrs['observaciones'] = (
                attrs['observaciones'].strip()
            )

        return attrs   