from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# Association table for Professor <-> Industry (Many-to-Many)
professor_industries = Table('professor_industries', Base.metadata,
    Column('professor_id', Integer, ForeignKey('professors.id'), primary_key=True),
    Column('industry_id', Integer, ForeignKey('industries.id'), primary_key=True)
)

# Association table for Professor <-> Sector (Many-to-Many)
professor_sectors = Table('professor_sectors', Base.metadata,
    Column('professor_id', Integer, ForeignKey('professors.id'), primary_key=True),
    Column('sector_id', Integer, ForeignKey('sectors.id'), primary_key=True)
)

class Professor(Base):
    __tablename__ = 'professors'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    department = Column(String)
    bio = Column(Text)
    image_url = Column(String)
    
    industries = relationship('Industry', secondary=professor_industries, back_populates='professors')
    sectors = relationship('Sector', secondary=professor_sectors, back_populates='professors')

    def __repr__(self):
        return f"<Professor(name='{self.name}', department='{self.department}')>"

class Industry(Base):
    __tablename__ = 'industries'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    professors = relationship('Professor', secondary=professor_industries, back_populates='industries')

    def __repr__(self):
        return f"<Industry(name='{self.name}')>"

class Sector(Base):
    __tablename__ = 'sectors'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    professors = relationship('Professor', secondary=professor_sectors, back_populates='sectors')

    def __repr__(self):
        return f"<Sector(name='{self.name}')>"

def init_db(db_path='sqlite:///data/faculty_v2.db'):
    # Ensure directory exists if using sqlite file
    if db_path.startswith('sqlite:///'):
        import os
        path = db_path.replace('sqlite:///', '')
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

if __name__ == "__main__":
    # Initialize DB when run directly
    import os
    os.makedirs('data', exist_ok=True)
    init_db()
    print("Database initialized.")
