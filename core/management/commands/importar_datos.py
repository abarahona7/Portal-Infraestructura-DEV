import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Usuario, Equipamiento, PerfilGenerico, IP

class Command(BaseCommand):
    help = 'Importa datos iniciales desde USUARIOS SIMI.xlsx y BARRIDO IP OFICIAL.xlsx'

    def handle(self, *args, **options):
        if not settings.ALLOW_LEGACY_IMPORT:
            raise CommandError('Importador legacy deshabilitado. Defina ALLOW_LEGACY_IMPORT=True solo para una migración controlada.')
        self.stdout.write(self.style.SUCCESS('--- Iniciando Importación de Datos Completa ---'))

        # -------------------------------------------------------------
        # 1. IMPORTAR USUARIOS Y EQUIPOS (NTBK, CEL, TBIT, BAM)
        # -------------------------------------------------------------
        file_simi = "USUARIOS SIMI.xlsx"
        
        try:
            df_raw = pd.read_excel(file_simi, sheet_name='CATASTRO DE USUARIOS Y EQUIPOS', skiprows=8)
            
            usuarios_creados = 0
            equipos_creados = 0

            for _, row in df_raw.iterrows():
                usuario_red = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                nombre_completo = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''

                if not usuario_red or usuario_red in ['nan', 'None', ''] or not nombre_completo or nombre_completo in ['nan', 'None', '']:
                    continue

                usuario_obj, created = Usuario.objects.update_or_create(
                    usuario_red=usuario_red,
                    defaults={
                        'nombre_completo': nombre_completo,
                        'correo_corp': str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else f"{usuario_red}@farmaciasdoctorsimi.cl",
                        'dpto_area': str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else 'N/A',
                        'cargo': str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else 'N/A',
                        'hostname': str(row.iloc[7]).strip() if pd.notna(row.iloc[7]) and str(row.iloc[7]).strip() != 'FALTA' else None,
                        'gmail': str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else None,
                        'sif': True if str(row.iloc[8]).strip().upper() == 'SI' else False,
                        'vpn_cisco': True if str(row.iloc[9]).strip().upper() == 'SI' else False,
                    }
                )
                if created:
                    usuarios_creados += 1

                secciones_equipos = [
                    ('NTBK', 10, 11, 12, 13), # Notebook
                    ('CEL',  17, 18, 19, 21), # Celular
                    ('TBIT', 26, 27, 28, 29), # Tablet
                    ('BAM',  34, 35, 36, 37), # BAM
                ]

                for tipo, idx_marca, idx_modelo, idx_serie, idx_af in secciones_equipos:
                    serie = str(row.iloc[idx_serie]).strip() if pd.notna(row.iloc[idx_serie]) else None
                    
                    if serie and serie not in ['nan', 'FALTA', 'N/A', '-', 'None']:
                        marca = str(row.iloc[idx_marca]).strip() if pd.notna(row.iloc[idx_marca]) else 'N/I'
                        modelo = str(row.iloc[idx_modelo]).strip() if pd.notna(row.iloc[idx_modelo]) else 'N/I'
                        af = str(row.iloc[idx_af]).strip() if pd.notna(row.iloc[idx_af]) else None

                        Equipamiento.objects.update_or_create(
                            numero_serie=serie,
                            defaults={
                                'usuario': usuario_obj,
                                'tipo': tipo,
                                'marca': marca if marca != 'nan' else 'N/I',
                                'modelo': modelo if modelo != 'nan' else 'N/I',
                                'af': af if af != 'nan' else None,
                                'estado': 'ASIGNADO'
                            }
                        )
                        equipos_creados += 1

            self.stdout.write(self.style.SUCCESS(f'Usuarios procesados: {usuarios_creados}'))
            self.stdout.write(self.style.SUCCESS(f'Equipos registrados: {equipos_creados}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error procesando Usuarios/Equipos: {e}'))

# -------------------------------------------------------------
        # 2. IMPORTAR PERFILES GENÉRICOS (UPDATE OR CREATE)
        # -------------------------------------------------------------
        try:
            df_gen = pd.read_excel(file_simi, sheet_name='PERFILES GENÉRICOS', skiprows=4)
            perfiles_creados = 0

            for _, row in df_gen.iterrows():
                nombre = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
                usr = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else None
                pwd = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else None
                correo = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else None
                dpto = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else None
                obs = str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else ''

                # Ignorar encabezados o filas sin usuario
                if not usr or usr in ['nan', 'NOMBRE DE USUARIO', 'None', ''] or nombre == 'NOMBRE':
                    continue

                if correo and ('@' not in correo or correo == 'CORREO'):
                    correo = None

                tipo_cuenta = 'O365' if 'Office 365' in obs or '365' in obs else 'ONPREMISE'

                PerfilGenerico.objects.update_or_create(
                    usuario=usr,
                    defaults={
                        'nombre': nombre if nombre and nombre != 'nan' else usr,
                        'password': pwd if pwd and pwd != 'nan' else None,
                        'correo': correo,
                        'dpto_area': dpto if dpto and dpto != 'nan' else None,
                        'tipo': tipo_cuenta
                    }
                )
                perfiles_creados += 1

            self.stdout.write(self.style.SUCCESS(f'Perfiles Genéricos procesados: {perfiles_creados}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error procesando Perfiles Genéricos: {e}'))
            
        # -------------------------------------------------------------
        # 3. CRUCE BARRIDO IP (HOJAS 1 Y 2)
        # -------------------------------------------------------------
        file_ip = "BARRIDO IP OFICIAL.xlsx"
        hojas_ip = ['172.23.1.0 ESTÁTICO', '172.25.1.0 DHCP']
        
        try:
            xls_ip = pd.ExcelFile(file_ip)
            ips_actualizadas = 0

            for sheet in hojas_ip:
                if sheet in xls_ip.sheet_names:
                    df_ip = pd.read_excel(xls_ip, sheet_name=sheet, skiprows=2)
                    
                    for _, row in df_ip.iterrows():
                        ip = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                        desc = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''

                        if ip and ip not in ['nan', 'DIRECCION IP', 'None', ''] and desc and desc not in ['LIBRE', 'nan', 'DESCRIPCION', 'None', '']:
                            usuarios = Usuario.objects.all()
                            for u in usuarios:
                                # Coincidencia flexible por nombre completo o por usuario de red
                                if u.nombre_completo and (
                                    u.nombre_completo.lower() in desc.lower()
                                    or desc.lower() in u.nombre_completo.lower()
                                    or u.usuario_red.lower() in desc.lower()
                                ):
                                    # Liberar otra IP que pudiera tener asignada
                                    IP.objects.filter(
                                        usuario=u
                                    ).exclude(
                                        direccion_ip=ip
                                    ).update(
                                        usuario=None,
                                        estado='LIBRE'
                                    )

                                    # Crear la IP si no existe o utilizar la existente
                                    ip_obj, _ = IP.objects.get_or_create(
                                        direccion_ip=ip,
                                        defaults={
                                            'estado': 'RESERVADA'
                                        }
                                    )

                                    ip_obj.usuario = u
                                    ip_obj.estado = 'RESERVADA'
                                    ip_obj.asignado_otro = None
                                    ip_obj.save(
                                        update_fields=[
                                            'usuario',
                                            'estado',
                                            'asignado_otro'
                                        ]
                                    )

                                    ips_actualizadas += 1
                                    break

            self.stdout.write(self.style.SUCCESS(f'IPs mapeadas ({", ".join(hojas_ip)}): {ips_actualizadas}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error procesando Barrido IP: {e}'))