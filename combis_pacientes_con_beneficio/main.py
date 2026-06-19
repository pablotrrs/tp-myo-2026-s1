from combis_pacientes_con_beneficio import resolver
from lector_datos_beneficios import leer

if __name__ == "__main__":
    ruta_archivo = "combis_pacientes_con_beneficio/input_combis_beneficios.txt"  
    p, t, b, tol, c, caps, coefs, dists = leer(ruta_archivo)
    resolver(p, t, b, tol, c, caps, coefs, dists)