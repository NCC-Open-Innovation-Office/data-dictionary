from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Entry(Base):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(Text, nullable=False)
    definition = Column(Text, nullable=False)
    abbreviation = Column(Text)
    dataType = Column(Text)
    inputFormat = Column(Text)
    variations = Column(Text)
    owner = Column(Text)
    stewards = Column(Text)
    classification = Column(
        Text,
        nullable=False,
        default='public',
        server_default='public',
    )
    discussion = Column(Text)
    ddId = Column(Text)
    createdAt = Column(String(64), nullable=False)
    updatedAt = Column(String(64), nullable=False)

    tags = relationship(
        'Tag',
        secondary='entry_tags',
        back_populates='entries',
    )
    outgoing_links = relationship(
        'EntryLink',
        foreign_keys='EntryLink.source_entry_id',
        back_populates='source_entry',
        cascade='all, delete-orphan',
    )
    incoming_links = relationship(
        'EntryLink',
        foreign_keys='EntryLink.target_entry_id',
        back_populates='target_entry',
        cascade='all, delete-orphan',
    )
    definitions = relationship(
        'EntryDefinition',
        back_populates='entry',
        cascade='all, delete-orphan',
    )


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    color = Column(
        Text,
        nullable=False,
        default='#004C8E',
        server_default='#004C8E',
    )
    createdAt = Column(String(64), nullable=False)

    entries = relationship(
        'Entry',
        secondary='entry_tags',
        back_populates='tags',
    )
    definitions = relationship(
        'EntryDefinition',
        back_populates='tag',
        cascade='all, delete-orphan',
    )


class EntryTag(Base):
    __tablename__ = 'entry_tags'

    entry_id = Column(
        Integer,
        ForeignKey('entries.id', ondelete='CASCADE'),
        nullable=False,
    )
    tag_id = Column(
        Integer,
        ForeignKey('tags.id', ondelete='CASCADE'),
        nullable=False,
    )

    __table_args__ = (PrimaryKeyConstraint('entry_id', 'tag_id'),)


class EntryLink(Base):
    __tablename__ = 'entry_links'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_entry_id = Column(
        Integer,
        ForeignKey('entries.id', ondelete='CASCADE'),
        nullable=False,
    )
    target_entry_id = Column(
        Integer,
        # ON DELETE handled by the ORM cascade on Entry.incoming_links;
        # MSSQL rejects multiple cascade paths to the same table, so the
        # target side uses the default NO ACTION.
        ForeignKey('entries.id'),
        nullable=False,
    )
    link_type = Column(
        Text,
        nullable=False,
        default='see_also',
        server_default='see_also',
    )
    createdAt = Column(String(64), nullable=False)

    source_entry = relationship(
        'Entry',
        foreign_keys=[source_entry_id],
        back_populates='outgoing_links',
    )
    target_entry = relationship(
        'Entry',
        foreign_keys=[target_entry_id],
        back_populates='incoming_links',
    )


class EntryDefinition(Base):
    __tablename__ = 'entry_definitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(
        Integer,
        ForeignKey('entries.id', ondelete='CASCADE'),
        nullable=False,
    )
    tag_id = Column(
        Integer,
        ForeignKey('tags.id', ondelete='CASCADE'),
        nullable=False,
    )
    definition = Column(Text, nullable=False)
    createdAt = Column(String(64), nullable=False)
    updatedAt = Column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'entry_id',
            'tag_id',
            name='uq_entry_definitions_entry_tag',
        ),
    )

    entry = relationship('Entry', back_populates='definitions')
    tag = relationship('Tag', back_populates='definitions')


class ChangeHistory(Base):
    __tablename__ = 'change_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(64), nullable=False)
    action = Column(Text, nullable=False)
    term = Column(Text, nullable=False)
    oldData = Column(Text)
    newData = Column(Text)
    discussion = Column(Text)
    user = Column(Text, nullable=False)