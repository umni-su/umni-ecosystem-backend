from classes.ecosystem import Ecosystem


def get_ecosystem():
    return Ecosystem()


def get_crypto():
    return get_ecosystem().crypto
