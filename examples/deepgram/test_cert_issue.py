# pip install cryptography
import _ssl
from cryptography import x509


def find_dst_cert(store_name) -> bool:
    """
    Find the problematic DST certificate
    """
    for cert, encoding_type, trust in _ssl.enum_certificates(store_name):
        decoded_cert = x509.load_der_x509_certificate(cert)

        if str(decoded_cert.issuer).find('DST Root') > 0:
            if store_name == 'CA':
                print(f'Certificate Store: {store_name} - "Current User -> Intermediate Certification Authorities -> Certificates -> Certificates"')
            elif store_name == 'ROOT':
                print(f'Certificate Store: {store_name} - "Local Computer -> Trusted Root Certificate Authorities -> Certificates"')
            print(f'Potentially problematic certificate : {decoded_cert.issuer}')
            # print(cert)
            print(f'{decoded_cert.serial_number}')
            print('---------------------------------------------------')
            return True
    return False

print('Determining if you are potentially impacted by the expired DST certificate.')

found: bool = find_dst_cert(store_name="CA")
found = found or find_dst_cert(store_name="ROOT")

if found:
    print('The potentially problematic certificate exists in certificate store.')
    print('Removal of the certificate from certificate store will not impact other operations.')
    print('Browsers that need the certificate will put it in the cert stores again.')
else:
    print('The problematic certificate is not in the certificate stores.')
