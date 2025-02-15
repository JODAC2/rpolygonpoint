from pyspark.sql import DataFrame
from rpolygonpoint.utils.spark import spark, _storage_level_, unpersist
from rpolygonpoint.utils.functions import to_list, write_persist
from rpolygonpoint.utils.functions import get_delimiter_rectangle
from rpolygonpoint.utils.functions import get_polygon_side
from rpolygonpoint.utils.functions import get_polygon_mesh
from rpolygonpoint.utils.functions import get_container_rectangle
from rpolygonpoint.utils.functions import get_container_polygon


def as_data_frame(df, path) -> DataFrame:
    """"
    As spark DataFrame
    ------
        If df is spark DataFrame then return df
        other wise load parquet in path
    """

    if type(df) is DataFrame:
       
        return df

    else:
       
        df = spark.read.parquet(path)
       
        return df


class SetContainerPolygon(object):
    """
    Set methods to class ContainerPolygon
    """

    _spark = spark
    
    # Nombre de tablas para preprocesor
    _tbl_delimiter_rectangle = "t_rpp_delimiter_rectangle"
    _tbl_polygon_side = "t_rpp_polygon_side"
    _tbl_polygon_mesh = "t_rpp_polygon_mesh"
    
    # Ruta de tablas para preprocesor
    _path_delimiter_rectangle = None
    _path_polygon_side = None
    _path_polygon_mesh = None
    
    def __init__(self, df_polygon=None):
        """
        Default values to parameters of class ContainerPolygon
        """

        self.df_polygon = df_polygon
        self.polygon_id = ["polygon_id"]
        self.coords = ["coord_x", "coord_y"]
        self.path_data = None
        self.point_seq = "point_seq"
        self.mesh_split = 2
        self.mesh_level = 4
        self.earned_prop = 0.7
        
        self.partition_delimiter_rectangle = 1
        self.partition_polygon_side = 1
        self.partition_polygon_mesh = 1
    
    def set_df_polygon(self, df):
        self.df_polygon = df
    
    def set_polygon_id(self, id):
        self.polygon_id = id
    
    def set_coords(self, coords):
        self.coords = coords
    
    def set_path_data(self, path):
        self.path_data = path
        self._set_paths()
    
    def set_point_seq(self, seq):
        self.point_seq = seq
    
    def set_mesh_split(self,split):
        self.mesh_split = split
    
    def set_mesh_level(self, level):
        self.mesh_level = level
    
    def set_earned_prop(self, prop):
        self.earned_prop = prop
    
    def set_partition_delimiter_rectangle(self, partition):
        self.partition_delimiter_rectangle = partition
    
    def set_partition_polygon_side(self, partition):
        self.partition_polygon_side = partition
    
    def set_partition_polygon_mesh(self, partition):
        self.partition_polygon_mesh = partition
    
    def _set_paths(self):
        """
        Update paths to preprocesor
        """

        if self.path_data is not None:
            
            self._path_delimiter_rectangle = self.path_data + self._tbl_delimiter_rectangle
            self._path_polygon_side = self.path_data + self._tbl_polygon_side
            self._path_polygon_mesh = self.path_data + self._tbl_polygon_mesh

        else:
            
            self._path_delimiter_rectangle = None
            self._path_polygon_side = None
            self._path_polygon_mesh = None


class MeshContainerPolygon(SetContainerPolygon):
    """
    Method to get polygon mesh - cell type
    """
    
    def __init__(self):
        
        super().__init__()
    
    def get_polygon_mesh(self):
        """
        Polygon mesh - cell type
        """
    
        self._delimiter_reactangle()
        self._polygon_side()
        self._polygon_mesh()
    
    def load_polygon_mesh(self):
        """
        Load preprocesor
        """

        self.df_delimiter_rectangle = self._spark.read.parquet(self._path_delimiter_rectangle)
        self.df_polygon_side = self._spark.read.parquet(self._path_polygon_side)
        self.df_polygon_mesh = self._spark.read.parquet(self._path_polygon_mesh)
    
    def _delimiter_reactangle(self):
        """
        Delimiter rectangle
        """

        df_delimiter_rectangle = get_delimiter_rectangle(
            df_polygon=self.df_polygon, 
            polygon_id=self.polygon_id, 
            coords=self.coords, 
            path=self._path_delimiter_rectangle,
            partition=self.partition_delimiter_rectangle
        )

        self.df_delimiter_rectangle = as_data_frame(df_delimiter_rectangle, self._path_delimiter_rectangle)
    
    def _polygon_side(self):
        """
        Polygon sides
        """
        
        df_polygon_side = get_polygon_side(
            df_polygon=self.df_polygon,
            polygon_id=self.polygon_id,
            coords=self.coords,
            point_seq=self.point_seq,
            path=self._path_polygon_side,
            partition=self.partition_polygon_side
        )

        self.df_polygon_side = as_data_frame(df_polygon_side, self._path_polygon_side)
    
    def _polygon_mesh(self):
        """
        Polygon mesh - cell type
        """
        
        df_polygon_mesh = get_polygon_mesh(
            df_delimiter_rectangle=self.df_delimiter_rectangle, 
            df_polygon_side=self.df_polygon_side, 
            polygon_id=self.polygon_id,
            coords=self.coords,
            split=self.mesh_split,
            level=self.mesh_level,
            prop=self.earned_prop, 
            path=self._path_polygon_mesh,
            partition=self.partition_polygon_mesh
        )

        self.df_polygon_mesh = as_data_frame(df_polygon_mesh, self._path_polygon_mesh)


class ContainerPolygon(MeshContainerPolygon):
    """
    Main class ContainerPolygon
    """
    
    def __init__(self, df_polygon=None):
        
        super().__init__()
        
        self.df_polygon = df_polygon
    
    def get_container_polygon(self, df_point, point_id="point_id", add_cols=[], path=None, partition=None) -> DataFrame:
        """
        Polygon container
        """

        mesh_polygon_id = to_list(self.polygon_id)
        _point_id = to_list(point_id)

        # Identificar posible poligono al que pertencese usando poligono delimitador
        # Si se encuentran las columnas self.polygon_id se hara se hara el cruce por estas
        df_container_rectangle = get_container_rectangle(
            df_point=df_point, 
            df_delimiter_rectangle=self.df_delimiter_rectangle, 
            polygon_id=self.polygon_id,
            coords=self.coords
        )
        
        # Identiicar celda a la que pertence el punto
        df_mesh_delimiter_rectangle = get_delimiter_rectangle(
            df_polygon=self.df_polygon_mesh, 
            polygon_id=mesh_polygon_id + ["cell_id", "cell_type"], 
            coords=self.coords
        )
        
        df_container_rectangle = get_container_rectangle(
            df_point=df_container_rectangle, 
            df_delimiter_rectangle=df_mesh_delimiter_rectangle, 
            coords=self.coords,
            polygon_id=self.polygon_id, 
            add_cols=["cell_id", "cell_type"]
        )
        
        # Puntos que estan en celda tipo undecided
        df_cell_undecided = df_container_rectangle\
            .filter(
                "cell_type = 'undecided'"
            ).select(
                mesh_polygon_id + _point_id + self.coords

            )
        
        # Validar si el punto esta dentro del polygon
        df_container_polygon = get_container_polygon(
            df_point=df_cell_undecided, 
            df_polygon_side=self.df_polygon_side, 
            polygon_id=self.polygon_id,
            point_id=_point_id, 
            coords=self.coords
        )
        
        # Container Polygon
        df_cp1 = df_container_rectangle\
            .filter(
                "cell_type = 'inside'"
            ).select(
                _point_id + mesh_polygon_id
            )

        df_cp2 = df_container_polygon\
            .select(
                _point_id + mesh_polygon_id
            )
        
        _add_cols = [ci for ci in add_cols if ci not in self.coords]

        df_container_polygon = df_cp1.union(df_cp2)\
            .join(
                df_point.select(_point_id + self.coords + _add_cols), 
                _point_id, 
                "inner"
            ).distinct()

        df_container_polygon = write_persist(
            df=df_container_polygon, 
            path=path,
            storage_level=_storage_level_,
            alias="ContainerPolygon",
            partition=partition
        )
        
        unpersist(df_container_rectangle, "ContainerRectangle")
        unpersist(df_mesh_delimiter_rectangle, "DelimiterRectangle-MeshCell")
        unpersist(df_container_rectangle, "ContainerRectangle-MeshCell")
        unpersist(df_container_polygon, "ContainerPolygon-Undecided")
    
        return df_container_polygon
