import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Membro
from api.serializers import passar_cargo

API_URL = 'https://neo.certi.org.br/api/proxy/users'

PASTA_FOTOS_LOCAIS = settings.BASE_DIR.parent / 'frontend' / 'public' / 'membros'


def foto_do_membro(usuario):
    arquivo = PASTA_FOTOS_LOCAIS / f"{usuario['username'].lower()}.webp"
    if arquivo.exists():
        return f'/membros/{arquivo.name}'
    return converter_foto(usuario)


def converter_foto(usuario):
    if usuario.get('pictureUrl'):
        return usuario['pictureUrl']

    drive_url = usuario.get('drivePhotoUrl')
    if not drive_url:
        return None

    match = re.search(r'/file/d/([\w-]+)', drive_url)
    if match:
        return f'https://drive.google.com/thumbnail?id={match.group(1)}&sz=w400'
    return drive_url


class Command(BaseCommand):
    help = (
        'Carga inicial: importa os membros atuais a partir da API do NEO (sigla = username). '
        'Depois disso, os membros são gerenciados pelo CRUD da própria aplicação.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Inclui também os membros inativos (por padrão só os ativos).',
        )
        parser.add_argument('--url', default=API_URL, help='URL da API de usuários.')

    def handle(self, *args, **options):
        try:
            requisicao = Request(options['url'], headers={'Accept': 'application/json'})
            with urlopen(requisicao, timeout=20) as resposta:
                usuarios = json.load(resposta)
        except (URLError, TimeoutError, json.JSONDecodeError) as erro:
            raise CommandError(f'Não foi possível ler a API: {erro}')

        if not options['todos']:
            usuarios = [u for u in usuarios if u.get('isActivate')]

        criados = atualizados = 0
        with transaction.atomic():
            for usuario in usuarios:
                nome = ' '.join(f"{usuario['firstName']} {usuario['lastName']}".split())
                sigla = usuario['username'].upper()
                cargo = ' '.join((usuario.get('role') or '').split())[:80]
                # Troca de semestre: quem ocupava este cargo o perde (a API é a fonte da verdade).
                passar_cargo(cargo, Membro.objects.filter(sigla=sigla).values_list('pk', flat=True).first())
                _, criado = Membro.objects.update_or_create(
                    sigla=sigla,
                    defaults={
                        'nome': nome[:120],
                        'email': usuario['email'].lower(),
                        'foto_url': foto_do_membro(usuario),
                        'cargo': cargo,
                    },
                )
                if criado:
                    criados += 1
                else:
                    atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'{len(usuarios)} membros processados: {criados} criados, {atualizados} atualizados.'
        ))
