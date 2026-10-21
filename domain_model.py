"""Dataset-scoped ATT&CK domain definitions and lossless record views. Flow: README.md."""
from dataclasses import dataclass, asdict
import re

OFFICIAL_LABELS = {'enterprise-attack': 'Enterprise', 'mobile-attack': 'Mobile', 'ics-attack': 'ICS'}
OFFICIAL_CHAINS = {'enterprise-attack': 'mitre-attack', 'mobile-attack': 'mitre-mobile-attack', 'ics-attack': 'mitre-ics-attack'}
OFFICIAL_ID = r'T\d{4}(?:\.\d{3})?'
CUSTOM_ID = r'[A-Za-z][A-Za-z0-9_.-]{0,127}'
DOMAIN_ID = r'[a-z][a-z0-9-]{0,63}'


def valid_domain(value):
    return isinstance(value, str) and bool(re.fullmatch(DOMAIN_ID, value))


def identifier_pattern(custom):
    return CUSTOM_ID if custom else OFFICIAL_ID


@dataclass(frozen=True)
class DomainDefinition:
    id: str
    name: str
    kill_chain_name: str
    reference_source: str = ''

    def payload(self):
        return asdict(self)

    @classmethod
    def read(cls, value):
        if not isinstance(value, dict) or set(value) - {'id', 'name', 'kill_chain_name', 'reference_source'}:
            raise ValueError('Domain definitions need id, name, kill_chain_name and reference_source fields.')
        if not valid_domain(value.get('id')):
            raise ValueError('Domain IDs use 1–64 lowercase letters, digits or hyphens and start with a letter.')
        for field in ('name', 'kill_chain_name', 'reference_source'):
            text = value.get(field, '')
            if (not isinstance(text, str) or not text.strip() or len(text) > 128
                    or any(ord(c) < 32 or c in '<>' for c in text)):
                raise ValueError('Domain ' + field + ' must be non-empty plain text of at most 128 characters.')
        return cls(**value)


def bundle_definitions(payload, objects):
    """Infer only unambiguous custom mappings; explicit definitions resolve ambiguity."""
    definitions = {d: DomainDefinition(d, label, OFFICIAL_CHAINS[d]) for d, label in OFFICIAL_LABELS.items()}
    raw = payload.get('x_ttp_studio_domains', [])
    if not isinstance(raw, list) or len(raw) > 32:
        raise ValueError('x_ttp_studio_domains must be a list of at most 32 domain definitions.')
    explicit = set()
    for value in raw:
        spec = DomainDefinition.read(value)
        if spec.id in explicit or spec.id in ('mitre-enterprise', 'mitre-mobile'):
            raise ValueError('Duplicate or reserved domain definition: ' + spec.id)
        explicit.add(spec.id)
        definitions[spec.id] = spec
    declared = {domain for obj in objects for domain in obj.get('x_mitre_domains', [])}
    if len(declared | explicit) > 32 or any(not valid_domain(d) or d in ('mitre-enterprise', 'mitre-mobile') for d in declared):
        raise ValueError('A custom Bundle supports at most 32 valid domain identifiers.')
    for domain in sorted(declared - definitions.keys()):
        records = [obj for obj in objects if obj['type'] == 'attack-pattern' and domain in obj.get('x_mitre_domains', [])
                   and not obj.get('revoked') and not obj.get('x_mitre_deprecated')]
        chains = {p['kill_chain_name'] for obj in records for p in obj.get('kill_chain_phases', [])}
        sources = {ref.get('source_name') for obj in records for ref in obj.get('external_references', [])
                   if ref.get('external_id')}
        if len(chains) != 1 or len(sources) != 1 or not next(iter(sources), None):
            raise ValueError(domain + ': ambiguous/missing kill chain or ID source; supply x_ttp_studio_domains.')
        definitions[domain] = DomainDefinition.read({'id': domain, 'name': domain,
            'kill_chain_name': next(iter(chains)), 'reference_source': next(iter(sources))})
    return definitions


class CatalogRecord(dict):
    """Dictionary bytes/JSON stay original; derived identity is scoped to one domain."""
    def __init__(self, obj=(), definition=None):
        super().__init__(obj)
        self.definition = definition

    @property
    def catalog_external_id(self):
        sources = {self.definition.reference_source} if self.definition and self.definition.reference_source else set(OFFICIAL_CHAINS.values())
        values = [ref.get('external_id', '') for ref in self.get('external_references', []) if ref.get('source_name') in sources
                  and ref.get('external_id')]
        if len(set(values)) > 1:
            raise ValueError('Conflicting external IDs for the configured reference source: ' + self.get('id', ''))
        return values[0] if values else ''


def domain_label(domain, catalog=None):
    if catalog is not None and domain in catalog.domain_definitions:
        return catalog.domain_definitions[domain].name
    return OFFICIAL_LABELS.get(domain, domain)
