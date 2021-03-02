from isbnlib import meta
from isbnlib.registry import bibformatters

SERVICE = 'openl'

# now you can use the service
isbn = '9780446310789'
isbn = '9780241295595'
bibtex = bibformatters['bibtex']
print(bibtex(meta(isbn, SERVICE)))
