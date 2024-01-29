import os
import time
from PIL import Image
from math import radians, cos, sin


class DummyBPY:
    class Data:
        objects = {"HGTarget": "dummy target", "HGCamera": "dummy camera"}

    class Ops:
        class Render:
            render = lambda *a, **kw: time.sleep(0)
        class WM:
            open_mainfile = lambda *a, **kw: None
        wm = WM()
        render = Render()
        
    class Context:
        class BlendData:
            filepath = 'file.blend'
        class Scene:
            class Render:
                class ImageSettings:
                    file_format = None
                render = lambda x: x
                image_settings = ImageSettings()
            render = Render()
        scene = Scene()
        blend_data = BlendData()

    class Path:
        basename = lambda x, y: y

    def __init__(self):
        self.ops = self.Ops()
        self.data = self.Data()
        self.path = self.Path()
        self.context = self.Context()


try:
    import bpy
except:
    bpy = DummyBPY()


def _remap(x,a,b,c,d):
    y=(x-a)/float((b-a))*(d-c)+c
    return round(y, 2)


class Blender:
    def __init__(self,
                 out_path,
                 frame_count,
                 object_name="HGTarget",
                 camera_name="HGCamera",
                 camera_dimension=600):

        self.object_name = object_name
        self.camera_name = camera_name

        self.frame_count = frame_count
        self.out_path = out_path

        self.dimension = camera_dimension
        self.file = bpy.path.basename(bpy.context.blend_data.filepath)

        self.object = None
        self.camera = None
        self.scene = None

        self._frame_index = 1

        self._load_check_scene_file()

    def __repr__(self):
        return f'<Blender: scene:{self.file}, camera={self.camera_name}, object={self.object_name}, dimension={self.dimension} >'

    def _load_check_scene_file(self):
        assert self.object_name in bpy.data.objects, f"Missing object {self.object_name}"
        assert self.camera_name in bpy.data.objects, f"Missing camera {self.camera_name}"

        self.scene = bpy.context.scene
        self.object = bpy.data.objects[self.object_name]
        self.camera = bpy.data.objects[self.camera_name]

    def move_camera_to_angle(self, angle_right, angle_up, offset_up=0, offset_right=0, distance=None):
        if type(bpy) == DummyBPY:
            print(f"Dummy BPY camera move: {angle_right}, {angle_up}")
            return
        # print(angle_right, angle_up, distance)
        distance = distance if distance else (self.camera.location - self.object.location).length

        angle_right = angle_right if angle_right > 0 else (360-abs(angle_right))    
        angle_up = angle_up if angle_up > 0 else (360-abs(angle_up))

        # print(angle_right, angle_up, distance)

        right_obj_rotation = self.object.rotation_euler.z
        up_obj_rotation = self.object.rotation_euler.y

        up_rotation_angle = radians(angle_up + offset_up)
        right_rotation_angle = radians(angle_right + offset_right)

        x = self.object.location.x + distance * cos(right_rotation_angle + right_obj_rotation)
        y = self.object.location.y + distance * sin(right_rotation_angle + right_obj_rotation)
        z = self.object.location.z + distance * sin(up_rotation_angle + up_obj_rotation)
        # print(x, y, z)
        self.camera.location.x = x
        self.camera.location.y = y
        self.camera.location.z = z

        # Point the camera towards the object
        direction = (self.object.location - self.camera.location).normalized()
        self.camera.rotation_mode = 'QUATERNION'
        self.camera.rotation_quaternion = direction.to_track_quat('Z', 'X')

    def lock_camera_to_object(self):
        if "Limit Distance" not in self.camera.constraints:
            limit_distance_constraint = self.camera.constraints.new(type='LIMIT_DISTANCE')
            limit_distance_constraint.target = self.object
            limit_distance_constraint.limit_mode = 'LIMITDIST_ONSURFACE'
            limit_distance_constraint.use_transform_limit = True

        # Add 'Track To' constraint to the camera
        if "Track To" not in self.camera.constraints:
            track_to_constraint = self.camera.constraints.new(type='TRACK_TO')
            track_to_constraint.target = self.object
            track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'
            track_to_constraint.up_axis = 'UP_Y'

    def render_file(self, 
                    x_index,
                    y_index,
                    right_angle,
                    up_angle):

        print(f"Render file (frame {self._frame_index} of {self.frame_count}):\n"
              f"  Scene: {self.file}\n"
              f"   X:{x_index}, Y:{y_index}\n"
              f"   R:{right_angle}, U:{up_angle}\n")
        self.scene.render.filepath = os.path.join(self.out_path, f"{self.file}_{x_index}_{y_index}_{right_angle}_{up_angle}.bmp")
        print(f"   File: {self.scene.render.filepath}\n")
        self.scene.render.image_settings.file_format = "BMP"
        self.scene.render.resolution_x = self.dimension
        self.scene.render.resolution_y = self.dimension
        print(f"   XY Dimension: {self.dimension}\n\n")
        self.scene.render.pixel_aspect_x = 1
        self.scene.render.pixel_aspect_y = 1
        bpy.ops.render.render(write_still=True)
        print(f"Render of frame {self._frame_index} of {self.frame_count} complete\n\n")
        self._frame_index += 1


class HogelProcessor:
    def __init__(self, hogen):
        self.hogen = hogen

    def generate_preview(self):
        sized_dimension = self.hogen.slm_dimension * 4
        out_image = Image.new('RGB', (sized_dimension, sized_dimension))

        for k, v in sorted(self.hogen.grid.items()):
            # print(k, v)
            offset = (
                int((sized_dimension / self.hogen.image_count_xy) * (k[1])),
                int((sized_dimension / self.hogen.image_count_xy) * (k[0]))
            )

            resize = int(sized_dimension / self.hogen.image_count_xy)

            # print(offset)

            image = Image.open(v['file'])
            image = image.resize((resize, resize))
            out_image.paste(image, offset)
        out_filepath = os.path.join(self.hogen.out_path, 'preview.png')
        out_image.save(out_filepath, 'PNG')

        print(f"Wrote out preview: {out_filepath}")

class Hogen:
    def __init__(self,
                 blender_file,
                 slm_dimension=600,
                 incident_angle=45,
                 image_count_xy=100,
                 init_elev=30,
                 init_azi=45,
                 init_dist=10,
                 out_path="C:\\hogel\\"):

        self.slm_dimension = slm_dimension
        self.incident_angle = incident_angle
        self.image_count_xy = image_count_xy
        self.out_path = out_path

        self.init_elev = float(init_elev)
        self.init_azi = float(init_azi)
        self.init_dist = float(init_dist)

        self.blender = Blender(out_path, self.image_count_xy * self.image_count_xy)

        self._configure_camera()

        self.grid = {}

        self._generate_grid()

        self._render_images()

        self.hogel_processor = HogelProcessor(self)

        self.hogel_processor.generate_preview()

    def _configure_camera(self):
        if type(bpy) != DummyBPY:
            self.blender.lock_camera_to_object()

            self.blender.scene.render.resolution_x = self.slm_dimension
            self.blender.scene.render.resolution_y = self.slm_dimension
        else:
            print("Dummy BPY _configure_camera")

    def _render_images(self):
        print("Starting image renders\n\n")

        gen_file_list = []

        avg_render_time = None
        current_frame = 1

        for index, data in sorted(self.grid.items()):
            render_start = time.time()
            self.blender.move_camera_to_angle(data['angles']['az'], data['angles']['el'], distance=self.init_dist)
            self.blender.render_file(index[0], index[1], data['angles']['az'], data['angles']['el'])
            render_end = time.time()
            duration = render_end - render_start
            if not avg_render_time:
                avg_render_time = duration
            avg_render_time = (duration + avg_render_time) / 2
            est_time_remain = ((len(self.grid) - current_frame) * avg_render_time)
            print(f"+++ Remaining - Frames: {len(self.grid) - current_frame}, Time: ~{est_time_remain} seconds")
            self.grid[index]['file'] = self.blender.scene.render.filepath
            gen_file_list.append((index, self.blender.scene.render.filepath))
            current_frame += 1

        print(f"Generated files: {gen_file_list}")

    def _generate_grid(self):
        ia = self.incident_angle
        ie = self.init_elev
        iaz = self.init_azi
        ids = self.init_dist
        
        def constrain_360(value):
            # if value + 1 > 360:
            #     value = (360 - value)
            # if value < 0:
            #     value = (value + 360)
            return float(round(value, 2))

        el_start = constrain_360(ie-(ia/2))
        el_end = constrain_360(ie+(ia/2))
        
        az_start = constrain_360(iaz-(ia/2))
        az_end = constrain_360(iaz+(ia/2))

        print("Angle grid generation params:\n"
              "  Elevation:\n"
              f"    Start: {el_start}\n"
              f"    Center: {ie}\n"
              f"    End: {el_end}\n"
              "  Azimuth:\n"
              f"    Start: {az_start}\n"
              f"    Center: {iaz}\n"
              f"    End: {az_end}\n"
              "\n")

        def print_nonew(str_in):
            print(str_in, end=" ")

        for index_az in range(self.image_count_xy):
            az_print = (str(index_az) + ":").ljust(len(str(self.image_count_xy)))
            print_nonew(f"Row {az_print}")
            for index_el in range(self.image_count_xy):
                coord = (index_el, index_az)
                self.grid[coord] = {
                    'angles': {
                        'az': _remap(index_az, 0, self.image_count_xy-1, az_end, az_start),
                        'el': _remap(index_el, 0, self.image_count_xy-1, el_end, el_start)
                    },
                    'file': ''
                }
                print_nonew(str(self.grid[coord]['angles']).ljust(16))
            print()
        print()
        
        # print(sorted(self.grid.keys()))


start_time = time.time()
hogen = Hogen(None, init_elev=0, init_azi=0, image_count_xy=40, incident_angle=135)
duration = time.time() - start_time
print(f"--- Took {duration} seconds ({duration / 60} min)")
