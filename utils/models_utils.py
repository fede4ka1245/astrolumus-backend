from random import randint


def generate_new_password():
    return str(randint(10000, 99999))
