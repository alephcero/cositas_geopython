import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from h3 import h3

def geopandas_a_geojson(gdf):
    geo = gpd.GeoSeries([file.geometry.iloc[0]]).geo_interface
    geo_geojson = geo_geojson['features'][0]['geometry']
    return geo_geojson

def clean_empty(gdf):
    gdf = gdf.loc[~gdf.geometry.is_empty, :]
    prior = len(gdf)
    gdf = gdf.loc[~gdf.geometry.isna(), :]
    post = len(gdf)
    print(prior - post, 'geoms emtpy or nan removed')
    return gdf

def llenar_poly_con_h3(gdf):
    #gdf geometry tiene que ser polygon
    gdf_geojson = gpd.GeoSeries([gdf.geometry.iloc[0]]).__geo_interface__
    gdf_geojson = gdf_geojson['features'][0]['geometry']

    indices_rio = h3.polyfill(
        geo_json=gdf_geojson,
        res=10, geo_json_conformant=True)
    return indices_rio


def clean_duplicates(gdf):
    duplicated_parcels = gdf.geometry.map(lambda g: g.wkb.hex()).duplicated()
    print('There are %i duplicated parcels' % duplicated_parcels.sum())
    gdf = gdf.loc[~duplicated_parcels, :]
    return gdf


def extract_poly_from_collection(indf):
    is_simple = indf.geometry.map(is_polygon)
    indf_simple = indf.loc[is_simple, :].copy()
    indf_multi = indf.loc[~is_simple, :].copy()

    outdf = gpd.GeoDataFrame(columns=indf_multi.columns)
    for idx, row in indf_multi.iterrows():
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row] * recs, ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom, 'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf, ignore_index=True)

        elif type(row.geometry) == GeometryCollection:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            for geom in row.geometry:
                if (type(geom) == Polygon) | (type(geom) == MultiPolygon):
                    gdf_coll = gpd.GeoDataFrame(columns=indf.columns)
                    gdf_coll = gdf_coll.append([row], ignore_index=True)
                    gdf_coll.loc[0, 'geometry'] = geom
                    multdf = multdf.append(gdf_coll)
            outdf = outdf.append(multdf, ignore_index=True)
    outdf = outdf.append(indf_simple)
    outdf = outdf.reset_index(drop=True)
    return outdf


def from_multy_to_poly(gdf):
    gdf.geometry = gdf.geometry.map(multy_to_poly)
    gdf = extract_poly_from_collection(gdf)
    return gdf


def get_first_poly(g):
    return g[0]


def is_multypolygon(g):
    return isinstance(g, type(MultiPolygon()))


def is_polygon(g):
    return isinstance(g, type(Polygon()))


def multy_to_poly(g):
    if is_multypolygon(g):
        if len(g) == 1:
            return get_first_poly(g)
        else:
            return g
    else:
        return g

def puntos_en_recorrido(recorrido, puntosCorte_n = 10):
    '''
    Esta funcion toma un recorrido (reco.geometry.iloc[0]) y
    una cantidad de puntos en % del recorrido
    y devuelve esos puntos sobre el recorrido
    '''

    puntosCorte = np.linspace(0,1,puntosCorte_n)
    crs = {'init': 'epsg:4326'}
    vertices = pd.DataFrame({'vertice':range(len(recorrido.coords)),
    'geometry':[Point(recorrido.coords[i]) for i in range(len(recorrido.coords))]})

    vertices = gpd.GeoDataFrame(vertices, crs=crs, geometry=vertices.geometry)

    vertices['LRSp'] = [recorrido.project(vertices.geometry.loc[i],normalized = True) for i in vertices.index]

    #detecto los vertices mas cercanos a mis puntos de corte
    deciles_recorrido = [vertices.iloc[(vertices.LRSp-i).abs().argsort()[:1],1].item() for i in puntosCorte]
    vertices = vertices.loc[deciles_recorrido,['vertice','geometry']]
    vertices.loc[:,'vertice'] = puntosCorte
    return vertices

def vertices_cada_Xmetros(geom,metros = 20):
    n_puntos = int((geom.length/metros)+1)
    percentiles = np.linspace(0,geom.length,n_puntos)
    return LineString([geom.interpolate(percentil,normalized=False) for percentil in percentiles])
