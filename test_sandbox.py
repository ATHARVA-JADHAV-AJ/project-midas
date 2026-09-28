from sandbox.restricted_runner import run_restricted

code = """
n_terms = 10
print('=== Fourier Series Expansion of a Square Wave ===')
print()
print('f(x) = (4/pi) * sum of (1/n)*sin(nx) for n=1,3,5,...')
print()

coefficients = {}
for n in range(1, n_terms * 2, 2):
    coeff = 4.0 / (math.pi * n)
    coefficients[n] = coeff
    print(f'  n={n}: b_n = 4/(pi*{n}) = {coeff:.6f}')

print()
print('--- Partial Sum at x = pi/4 ---')
x = math.pi / 4
partial_sum = 0.0
for n in range(1, n_terms * 2, 2):
    term = coefficients[n] * math.sin(n * x)
    partial_sum = partial_sum + term
    print(f'  After n={n}: sum = {partial_sum:.6f}')

print()
print(f'Approximation at x=pi/4: {partial_sum:.6f}')
print(f'Expected (square wave = 1): 1.000000')

counter = {}
counter['a'] = 0
counter['a'] += 1
counter['a'] += 1
print(f'Augmented assignment test (expect 2): {counter["a"]}')
"""

sandbox_result = run_restricted(code, timeout_seconds=10)
print('EXIT:', sandbox_result['exit_code'])
print('STDOUT:', sandbox_result['stdout'][:2000])
if sandbox_result['stderr']:
    print('STDERR:', sandbox_result['stderr'][:500])
