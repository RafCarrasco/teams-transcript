"""Ring buffer de frames de áudio e utilitário de mix mono — lógica pura.

Este módulo não toca em hardware nem importa libs de áudio: só `numpy`.
Por isso é totalmente testável em qualquer ambiente.

`RingBuffer` é um buffer circular FIFO de amostras `float32`. A captura de
áudio roda em callbacks de outra thread (o callback do `sounddevice`), então
o produtor (callback) e o consumidor (thread que grava o WAV / processa)
acessam o buffer concorrentemente — daí o `threading.Lock`.

Quando o buffer enche, as amostras mais antigas são sobrescritas: para
captura de áudio em tempo real, perder o som antigo é preferível a bloquear
o callback de áudio (o que causaria estouros/glitches no driver).
"""

from __future__ import annotations

import threading

import numpy as np

# dtype canônico das amostras de áudio em todo o pipeline.
_DTYPE = np.float32


class RingBuffer:
    """Buffer circular FIFO de amostras de áudio `float32`, thread-safe.

    As amostras são mono (vetor 1-D). Multicanal deve ser reduzido a mono
    (ver `mix_to_mono`) antes de entrar aqui.

    Quando cheio, novas escritas sobrescrevem as amostras mais antigas —
    comportamento adequado para áudio em tempo real, onde nunca se quer
    bloquear o callback do driver.
    """

    def __init__(self, capacity: int) -> None:
        """Cria um buffer que comporta no máximo `capacity` amostras."""
        if capacity <= 0:
            raise ValueError("capacity deve ser positiva")
        self._capacity = int(capacity)
        # Armazenamento subjacente de tamanho fixo.
        self._data = np.zeros(self._capacity, dtype=_DTYPE)
        # _start: índice da amostra mais antiga. _size: quantas amostras válidas.
        self._start = 0
        self._size = 0
        self._lock = threading.Lock()

    # -- introspecção ------------------------------------------------------

    @property
    def capacity(self) -> int:
        """Número máximo de amostras que o buffer comporta."""
        return self._capacity

    def __len__(self) -> int:
        """Número de amostras válidas atualmente armazenadas."""
        with self._lock:
            return self._size

    @property
    def is_empty(self) -> bool:
        """`True` se não há amostras para ler."""
        with self._lock:
            return self._size == 0

    @property
    def is_full(self) -> bool:
        """`True` se o buffer está cheio (próxima escrita sobrescreve)."""
        with self._lock:
            return self._size == self._capacity

    # -- operações ---------------------------------------------------------

    def write(self, frames: np.ndarray) -> None:
        """Escreve `frames` no fim do buffer.

        O array é convertido para `float32` e deve ser 1-D. Se a escrita
        ultrapassar a capacidade, as amostras mais antigas são descartadas
        (overwrite). Escrever mais que `capacity` de uma vez mantém apenas
        as últimas `capacity` amostras.
        """
        frames = np.asarray(frames, dtype=_DTYPE)
        if frames.ndim != 1:
            raise ValueError("frames deve ser um array 1-D (mono)")

        with self._lock:
            n = frames.size
            if n == 0:
                return

            # Escrita maior que o buffer inteiro: só as últimas `capacity`
            # amostras importam — o resto seria sobrescrito de imediato.
            if n >= self._capacity:
                self._data[:] = frames[-self._capacity :]
                self._start = 0
                self._size = self._capacity
                return

            # Posição do primeiro slot livre (logo após a última amostra).
            end = (self._start + self._size) % self._capacity
            # A cópia pode dar a volta no fim do array: parte-se em dois pedaços.
            first = min(n, self._capacity - end)
            self._data[end : end + first] = frames[:first]
            if n > first:
                self._data[: n - first] = frames[first:]

            # Atualiza ocupação e, se houve overwrite, avança o início.
            overflow = self._size + n - self._capacity
            if overflow > 0:
                self._start = (self._start + overflow) % self._capacity
                self._size = self._capacity
            else:
                self._size += n

    def read(self, n: int) -> np.ndarray:
        """Remove e devolve até `n` amostras, da mais antiga para a mais nova.

        Se houver menos de `n` amostras, devolve só o que existe (pode ser
        um array vazio). O resultado é sempre um array `float32` 1-D novo
        (cópia — seguro para o chamador modificar).
        """
        with self._lock:
            count = min(n, self._size)
            out = np.empty(count, dtype=_DTYPE)
            if count == 0:
                return out

            # A leitura também pode dar a volta no fim do array.
            first = min(count, self._capacity - self._start)
            out[:first] = self._data[self._start : self._start + first]
            if count > first:
                out[first:] = self._data[: count - first]

            self._start = (self._start + count) % self._capacity
            self._size -= count
            return out


def mix_to_mono(loopback: np.ndarray, mic: np.ndarray) -> np.ndarray:
    """Soma dois sinais de áudio em um único canal mono, sem clipping.

    `loopback` é o som do sistema (o que sai pelos alto-falantes) e `mic` é
    o microfone. Cada entrada pode ser mono (1-D) ou multicanal (2-D, shape
    `(amostras, canais)`); canais são colapsados pela média.

    Os sinais são alinhados pelo menor comprimento (na captura ao vivo um
    stream pode entregar alguns frames a mais que o outro). A soma é então
    normalizada: se o pico absoluto passar de 1.0, o sinal inteiro é
    dividido por esse pico — garantindo amplitude em [-1, 1] e preservando
    a forma de onda relativa, em vez de cortar (clipar) os picos.

    Devolve um array `float32` 1-D.
    """
    lb = _to_mono_1d(loopback)
    mc = _to_mono_1d(mic)

    # Alinha pelo menor comprimento — streams ao vivo dessincronizam um pouco.
    length = min(lb.size, mc.size)
    mixed = lb[:length] + mc[:length]

    # Normalização: evita clipping dividindo pelo pico quando ele excede 1.0.
    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 1.0:
        mixed = mixed / peak

    return mixed.astype(_DTYPE, copy=False)


def _to_mono_1d(signal: np.ndarray) -> np.ndarray:
    """Converte um sinal para vetor mono 1-D `float32`.

    Aceita 1-D (já mono) ou 2-D `(amostras, canais)` — neste caso os canais
    são reduzidos pela média.
    """
    arr = np.asarray(signal, dtype=_DTYPE)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2:
        # Média ao longo do eixo de canais -> mono.
        return arr.mean(axis=1).astype(_DTYPE, copy=False)
    raise ValueError("sinal de áudio deve ter 1 ou 2 dimensões")
