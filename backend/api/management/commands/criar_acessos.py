from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Membro
from api.permissoes import CARGO_ADMIN, eh_cargo_admin
from api.serializers import sincronizar_usuario


class Command(BaseCommand):
    help = (
        'Cria o login (usuário = e-mail) dos membros que ainda não têm acesso, com a senha '
        f'informada. Não há papel a escolher: quem tem o cargo {CARGO_ADMIN} é Admin e os demais '
        'são Membros; o gerente de cada projeto é definido na equipe do projeto.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--senha', required=True, help='Senha inicial dos membros que ainda não têm acesso.')

    @transaction.atomic
    def handle(self, *args, **options):
        sem_acesso = list(Membro.objects.filter(user__isnull=True).order_by('sigla'))
        for membro in sem_acesso:
            sincronizar_usuario(membro, options['senha'])

        admins = [m.sigla for m in Membro.objects.order_by('sigla') if eh_cargo_admin(m.cargo)]
        if admins:
            self.stdout.write(f'  Admin (cargo {CARGO_ADMIN}): {", ".join(admins)}')
        else:
            self.stdout.write(self.style.WARNING(
                f'  Nenhum membro com o cargo {CARGO_ADMIN}: ninguém terá o papel de Admin.'
            ))
        self.stdout.write(self.style.SUCCESS(f'{len(sem_acesso)} acesso(s) criado(s).'))
