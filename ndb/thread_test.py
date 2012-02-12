"""A torture test to ferret out problems with multi-threading."""

import sys
import threading

from . import tasklets
from . import context


def main():
  num = 10
  try:
    num = int(sys.argv[1])
  except Exception:
    pass
  threads = []
  for i in range(num):
    t = threading.Thread(target=one_thread, args=(i, num,))
    t.start()
    threads.append(t)
  for t in threads:
    t.join()


@context.toplevel
def one_thread(_, num):
  yield fibonacci(num)
  ##sys.stdout.write('%d: %d --> %d\n' % (i, num, x))


@tasklets.tasklet
def fibonacci(n):
  """A recursive Fibonacci to exercise task switching."""
  if n <= 1:
    raise tasklets.Return(n)
  a = yield fibonacci(n - 1)
  b = yield fibonacci(n - 2)
  raise tasklets.Return(a + b)


if __name__ == '__main__':
  main()
