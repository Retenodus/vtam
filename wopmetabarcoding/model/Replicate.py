from wopmars.framework.database.Base import Base

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import validates


class Replicate(Base):
    __tablename__ = 'Replicate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_id = Column(Integer, ForeignKey('Biosample.sample_id'))
    marker_id = Column(Integer, ForeignKey('Marker.marker_id'))
    tag_id = Column(Integer, ForeignKey('TagPair.tag_id'))
    file_id = Column(Integer, ForeignKey('File.id'))
    name = Column(String(50), nullable=False)

    @validates('name')
    def validate_replicatename(self, key, replicate_name):
        if '_' in replicate_name:
            replicate_namebis = replicate_name.replace('_', '')
            assert replicate_namebis.isalnum()
        else:
            assert replicate_name.isalnum()
        return replicate_name