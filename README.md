# Pesas
Código para calcular **masa mínima** y **clase de pesa patrón** (OIML R111).

## Uso
```bash
python pesa_min_y_clase.py --calc mmin  --s 0.005 --d 0.01 --rrel 0.001 --k 2
python pesa_min_y_clase.py --calc clase --mass-g 2000 --tur 4 --s 0.005 --d 0.01
python pesa_min_y_clase.py --calc both  --s 0.005 --d 0.01 --rrel 0.001 --k 2 --mass-g 2000 --tur 4

