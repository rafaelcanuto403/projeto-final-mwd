import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Membro

API_URL = 'https://neo.certi.org.br/api/proxy/users'


def converter_foto(usuario):
    """Escolhe a melhor URL de foto disponível para usar direto em uma <img>."""
    if usuario.get('pictureUrl'):
        return usuario['pictureUrl']

    drive_url = usuario.get('drivePhotoUrl')
    if not drive_url:
        return None

    # Links do tipo ".../file/d/<ID>/view" não abrem em <img>; a miniatura abre.
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
                # split/join remove espaços duplicados vindos da API
                nome = ' '.join(f"{usuario['firstName']} {usuario['lastName']}".split())
                _, criado = Membro.objects.update_or_create(
                    sigla=usuario['username'].upper(),
                    defaults={
                        'nome': nome[:120],
                        'email': usuario['email'].lower(),
                        'foto_url': converter_foto(usuario),
                    },
                )
                if criado:
                    criados += 1
                else:
                    atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'{len(usuarios)} membros processados: {criados} criados, {atualizados} atualizados.'
        ))
