from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# -----------------------
# Exceções
# -----------------------
class InvalidRecipientError(Exception):
    pass


class UnsupportedMessageError(Exception):
    pass


# -----------------------
# Mensagens (Hierarchy)
# -----------------------
@dataclass
class Message(ABC):
    _text: str
    _send_date: Optional[datetime] = None

    def __post_init__(self):
        if self._send_date is None:
            self._send_date = datetime.now()

    @property
    def text(self) -> str:
        return self._text

    @property
    def send_date(self) -> datetime:
        return self._send_date

    @abstractmethod
    def metadata(self) -> dict:
        """Retorna metadados específicos do tipo de mensagem."""
        pass

    def __str__(self):
        return f"{self.__class__.__name__}(text={self.text!r}, send_date={self.send_date})"


@dataclass
class TextMessage(Message):
    def metadata(self) -> dict:
        return {"type": "text", "text": self.text}


class MediaMessage(Message, ABC):
    # A classe MediaMessage não precisa ser um dataclass, mas precisa de um construtor
    # que chame o construtor da classe base (Message) e defina seus atributos.
    def __init__(self, message: str, file_path: str, format: str, duration_seconds: Optional[int] = None):
        super().__init__(message)
        self._file_path = file_path
        self._format = format
        self._duration_seconds = duration_seconds # Adicionado para suportar o exemplo de vídeo

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def format(self) -> str:
        return self._format
    
    @property
    def duration_seconds(self) -> Optional[int]:
        return self._duration_seconds

    # Implementação do método abstrato 'metadata'
    def metadata(self) -> dict:
        meta = {
            "type": "media",
            "text": self.text,
            "file_path": self.file_path,
            "format": self.format,
        }
        if self.duration_seconds is not None:
            meta["duration_seconds"] = self.duration_seconds
        return meta


# Classes concretas ausentes no código original, mas usadas no 'main'
class PhotoMessage(MediaMessage):
    def __init__(self, message: str, file_path: str, format: str):
        # Fotos não costumam ter duração, então passamos None para duration_seconds
        super().__init__(message, file_path, format, duration_seconds=None)

    def metadata(self) -> dict:
        meta = super().metadata()
        meta["type"] = "photo"
        # Remove a duração, pois não se aplica a fotos
        meta.pop("duration_seconds", None)
        return meta


class FileMessage(MediaMessage):
    def __init__(self, message: str, file_path: str, format: str):
        # Arquivos não costumam ter duração, então passamos None para duration_seconds
        super().__init__(message, file_path, format, duration_seconds=None)

    def metadata(self) -> dict:
        meta = super().metadata()
        meta["type"] = "file"
        # Remove a duração, pois não se aplica a arquivos
        meta.pop("duration_seconds", None)
        return meta


# -----------------------
# Canais (Hierarchy)
# -----------------------
class Channel(ABC):
    """
    Canal abstrato. Cada canal precisa implementar send(message, recipient).
    """

    @abstractmethod
    def send(self, message: Message, recipient: str) -> None:
        pass


class PhoneChannel(Channel, ABC):
    """
    Canais que usam número de telefone como destinatário.
    """

    def _validate_phone(self, recipient: str) -> None:
        # validação simples: deve conter apenas dígitos, opcional '+' no início, e ter entre 8 e 15 dígitos (ex: +5511999998888)
        r = recipient.strip()
        if r.startswith("+"):
            r = r[1:]
        if not r.isdigit() or not (8 <= len(r) <= 15):
            raise InvalidRecipientError(f"Telefone inválido: {recipient!r}")


class UserChannel(Channel, ABC):
    """
    Canais que usam nome de usuário.
    """

    def _validate_username(self, recipient: str) -> None:
        r = recipient.strip()
        # validação simples: não vazio, sem espaços no início/fim
        if not r or len(r) > 50:
            raise InvalidRecipientError(f"Usuário inválido: {recipient!r}")


# Implementações concretas de canais
class WhatsAppChannel(PhoneChannel):
    def send(self, message: Message, recipient: str) -> None:
        self._validate_phone(recipient)
        # Aqui colocaria integração real com API do WhatsApp; por enquanto simulamos
        meta = message.metadata()
        # WhatsApp aceita texto, foto, vídeo, arquivos; exemplo de tratamento específico:
        print(f"[WhatsApp] Enviando para {recipient} -> tipo: {meta['type']}, texto: {meta.get('text')}")
        if meta['type'] != "text":
            print(f"  arquivo: {meta.get('file_path')} ({meta.get('format')})")
        # Simula sucesso
        print("  -> Enviado com sucesso via WhatsApp.")


class TelegramChannel(PhoneChannel, UserChannel):
    def send(self, message: Message, recipient: str) -> None:
        # Telegram pode usar número ou usuário; detectamos pelo formato:
        r = recipient.strip()
        if r.startswith("@") or (not r.startswith("+") and not r.replace("+", "").isdigit()):
            # trata como username
            self._validate_username(r)
        else:
            # trata como phone
            self._validate_phone(r)

        meta = message.metadata()
        print(f"[Telegram] Enviando para {recipient} -> tipo: {meta['type']}, texto: {meta.get('text')}")
        if meta['type'] != "text":
            print(f"  arquivo: {meta.get('file_path')} ({meta.get('format')})")
        print("  -> Enviado com sucesso via Telegram.")


class FacebookChannel(UserChannel):
    def send(self, message: Message, recipient: str) -> None:
        self._validate_username(recipient)
        meta = message.metadata()
        # Facebook geralmente usa usuário/pages/IDs — aqui tratamos genericamente
        print(f"[Facebook] Enviando para {recipient} -> tipo: {meta['type']}, texto: {meta.get('text')}")
        if meta['type'] != "text":
            print(f"  arquivo: {meta.get('file_path')} ({meta.get('format')})")
        print("  -> Enviado com sucesso via Facebook.")


class InstagramChannel(UserChannel):
    def send(self, message: Message, recipient: str) -> None:
        self._validate_username(recipient)
        meta = message.metadata()
        # Instagram tem restrições (ex.: vídeos e fotos com certos limites) — aqui apenas simulamos
        print(f"[Instagram] Enviando para {recipient} -> tipo: {meta['type']}, texto: {meta.get('text')}")
        if meta['type'] != "text":
            print(f"  arquivo: {meta.get('file_path')} ({meta.get('format')})")
        print("  -> Enviado com sucesso via Instagram.")


# -----------------------
# Função utilitária para enviar (demonstra polimorfismo)
# -----------------------
def send_message_to_channel(channel: Channel, message: Message, recipient: str) -> None:
    """
    Encapsula o envio e trata exceções de validação.
    """
    try:
        channel.send(message, recipient)
    except InvalidRecipientError as e:
        print(f"[Erro] destinatário inválido: {e}")
    except UnsupportedMessageError as e:
        print(f"[Erro] mensagem não suportada neste canal: {e}")
    except Exception as e:
        print(f"[Erro inesperado] {e}")


# -----------------------
# Exemplo de uso Interativo
# -----------------------
def get_user_input(prompt: str, default: Optional[str] = None) -> str:
    """Função auxiliar para obter entrada do usuário com um valor padrão."""
    if default:
        return input(f"{prompt} (Padrão: {default}): ") or default
    return input(f"{prompt}: ")

def create_message_from_input() -> Optional[Message]:
    """Cria uma mensagem com base na entrada do usuário."""
    print("\n--- Criar Mensagem ---")
    print("Tipos de Mensagem:")
    print("  1: Texto")
    print("  2: Foto")
    print("  3: Vídeo")
    print("  4: Arquivo")
    
    choice = get_user_input("Escolha o tipo de mensagem (1-4)", "1")
    text = get_user_input("Digite o texto da mensagem", "Mensagem de teste")

    if choice == '1':
        return TextMessage(text)
    
    elif choice in ('2', '3', '4'):
        file_path = get_user_input("Caminho do arquivo", "/tmp/arquivo_teste")
        file_format = get_user_input("Formato do arquivo (ex: jpg, mp4, pdf)", "txt")
        
        if choice == '2':
            return PhotoMessage(text, file_path, file_format)
        elif choice == '3':
            duration = get_user_input("Duração do vídeo em segundos", "60")
            try:
                duration_seconds = int(duration)
            except ValueError:
                print("[Aviso] Duração inválida. Usando 60 segundos.")
                duration_seconds = 60
            # MediaMessage é a classe base, mas para vídeo, podemos usar ela diretamente ou criar uma VideoMessage
            # Usaremos MediaMessage para simplificar, já que ela suporta duration_seconds
            return MediaMessage(text, file_path, file_format, duration_seconds)
        elif choice == '4':
            return FileMessage(text, file_path, file_format)
    
    else:
        print("[Erro] Opção de mensagem inválida.")
        return None

def main():
    wa = WhatsAppChannel()
    tg = TelegramChannel()
    fb = FacebookChannel()
    ig = InstagramChannel()

    channels = {
        '1': (wa, "WhatsApp"),
        '2': (tg, "Telegram"),
        '3': (fb, "Facebook"),
        '4': (ig, "Instagram"),
    }

    while True:
        print("\n=====================================")
        print("  Simulador de Envio de Mensagens")
        print("=====================================")
        print("Opções:")
        print("  1: Enviar Mensagem")
        print("  2: Testar Validações (Exemplos Fixos)")
        print("  0: Sair")
        
        main_choice = get_user_input("Escolha uma opção (0-2)", "1")

        if main_choice == '0':
            print("Saindo do simulador.")
            break
        
        elif main_choice == '1':
            message = create_message_from_input()
            if not message:
                continue

            print("\n--- Escolher Canal ---")
            print("Canais Disponíveis:")
            print("  1: WhatsApp (Telefone)")
            print("  2: Telegram (Telefone ou Usuário)")
            print("  3: Facebook (Usuário)")
            print("  4: Instagram (Usuário)")
            
            channel_choice = get_user_input("Escolha o canal (1-4)", "1")
            
            if channel_choice in channels:
                channel, name = channels[channel_choice]
                recipient = get_user_input(f"Digite o destinatário para {name}")
                
                print(f"\n=== Enviando via {name} ===")
                send_message_to_channel(channel, message, recipient)
            else:
                print("[Erro] Opção de canal inválida.")

        elif main_choice == '2':
            print("\n=== Executando Testes de Validação Fixos ===")
            
            # Mensagens de teste fixas
            txt = TextMessage("Olá! Esta é uma mensagem de texto para teste.")
            vid = MediaMessage("Veja este vídeo de teste", file_path="/tmp/video.mp4", format="mp4", duration_seconds=120)
            
            # Teste de número inválido
            print("\n--- Teste: número inválido (WhatsApp) ---")
            send_message_to_channel(wa, txt, "abc123")
            
            # Teste de username muito longo
            print("\n--- Teste: username muito longo (Instagram) ---")
            send_message_to_channel(ig, txt, "u" * 100)
            
            # Teste de envio de vídeo (usando Telegram)
            print("\n--- Teste: envio de vídeo (Telegram) ---")
            send_message_to_channel(tg, vid, "@usuario_valido")
            
            print("\nTestes de validação concluídos.")

        else:
            print("[Erro] Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()