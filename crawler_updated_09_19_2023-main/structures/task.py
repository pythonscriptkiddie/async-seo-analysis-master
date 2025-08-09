from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator, HttpUrl

class Warning(BaseModel):
    ts: datetime = Field(default=datetime.now())
    warning: str
    message: Optional[str]
    page_title : Optional[str]
    page_url : Optional[str]
    
    @staticmethod
    def split_warning(warning: str, splitter: str=':'):
        '''Returns the position of the first colon in the warnings'''
        match (split_position := warning.find(splitter)):
            case -1:
                return warning
            case _:
                return [warning[:split_position], warning[split_position+1:].strip()]
            
    @classmethod
    def factory(cls, data: str, page=None):
        '''Takes a warning string and returns a Warning object'''
        #split the warning into multiple parts
        split_warning = Warning.split_warning(warning=data)
        match len(split_warning):
            case 0:
                return None
            case 1:
                return cls(warning=split_warning[0])
            case 2:
                return cls(warning=split_warning[0],
                              message=split_warning[1])
            case _:
                try:
                    return cls(warning=split_warning[0],
                                  message=split_warning[1])
                except Exception as e:
                    return None