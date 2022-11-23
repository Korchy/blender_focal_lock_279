# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/blender_focal_lock_279

import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty
from bpy.types import Panel, PropertyGroup, Operator, Object, Camera
from bpy.app.handlers import persistent
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Focal Lock",
    "description": "Locks object in a camera's plane of focus",
    "author": "Nikita Akimov, Anson Savage <artstation.com/ansonsavage>, Nathan Craddock <nathancraddock.com>",
    "version": (1, 0, 2),
    "blender": (2, 79, 0),
    "location": "Properties area > Render tab > Focal Lock",
    "doc_url": "https://github.com/Korchy/blender_focal_lock_279",
    "tracker_url": "https://github.com/Korchy/blender_focal_lock_279",
    "support": "COMMUNITY",
    "category": "Camera",
    }


# HELPER FUNCTIONS

def distance_to_plane(ob):
    context = bpy.context
    scene = context.scene
    cam = scene.camera
    # Special thanks to batFINGER's answer here:
    # https://blender.stackexchange.com/questions/231817/how-to-obtain-the-vector-normal-to-the-camera-plane
    cam_axis = cam.matrix_world.to_3x3().normalized().col[2]
    cam_axis.negate()
    cam_loc = cam.matrix_world.translation
    v = ob.matrix_world.translation - cam_loc
    n = v.project(cam_axis)
    return n.length


def camera_track_constraint(context):
    # get camera track_to constraint
    return next((c for c in context.scene.camera.constraints if c.type == 'TRACK_TO'), None)


# WATCHER FUNCTIONS

def update_focus_object(self, context):
    settings = context.scene.camera.data.focal_lock
    update_enable_lock(self, context)   # run this so that all the original settings are made again
    # here's where all the code should go when the focus object is updated!
    if settings.enable_track:
        camera_track_constraint(context).target = settings.focus_object


# There is a bug here - when you enable the focus lock without having an object selected for
# tracking settings.focus_object is None. Shouldn't be too hard to fix though, just don't
# do anything when it is None :)
def update_enable_lock(self, context):
    # settings = context.object.data.focal_lock
    settings = context.scene.camera.data.focal_lock
    enable_lock = settings.enable_lock
    if enable_lock and settings.focus_object is not None:
        # Set original focal length
        # okay, figure out how to make this apply to just our camera
        settings.original_focal_length = context.scene.camera.data.lens
        # set current distance
        settings.original_distance = distance_to_plane(settings.focus_object)
        settings.focal_distance_ratio = settings.original_focal_length / settings.original_distance


def update_enable_track(self, context):
    settings = context.scene.camera.data.focal_lock

    # because you are only accessing enable_track once, no need to store in variable
    if settings.enable_track:
        track_constraint = context.scene.camera.constraints.new(type='TRACK_TO')
        track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
        track_constraint.up_axis = 'UP_Y'
        track_constraint.target = settings.focus_object
    else:
        track_constraint = camera_track_constraint(context)
        if track_constraint:
            context.scene.camera.constraints.remove(track_constraint)


@persistent
def update_focal_length(*agrs):
    # for each camera with focal_lock enabled...
    for camera in bpy.data.cameras:
        if camera.focal_lock.enable_lock and camera.focal_lock.focus_object is not None:
            currentDistance = distance_to_plane(camera.focal_lock.focus_object)
            camera.lens = currentDistance * (camera.focal_lock.focal_distance_ratio)
            # bpy.context.scene.camera.lens = currentDistance * (bpy.context.scene.camera_settings.focal_distance_ratio)
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            area.tag_redraw()


# OPERATORS

class BakeFocalLength(Operator):
    bl_idname = "wm.bake_focal_length"
    bl_label = "Bake Focal Length"

    def execute(self, context):
        scene = context.scene
        cam = scene.camera
        for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
            scene.frame_set(frame)
            cam.data.keyframe_insert(data_path="lens")
        return {'FINISHED'}


class ClearBakeFocalLength(Operator):
    bl_idname = "wm.clear_bake_focal_length"
    bl_label = "Clear Bake"

    def execute(self, context):
        scene = context.scene
        cam = scene.camera
        for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
            scene.frame_set(frame)
            cam.data.keyframe_delete(data_path="lens")
        return {'FINISHED'}


# PANELS

class FOCALLOCK_PT_FocalLock(Panel):
    bl_idname = 'focal_lock.panel'
    bl_category = "Focal Lock"
    bl_label = "Focal Lock"
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.camera and context.active_object == context.scene.camera

    def draw_header(self, context):
        cam = context.scene.camera.data
        settings = cam.focal_lock
        layout = self.layout
        layout.active = settings.enable_lock
        layout.prop(settings, "enable_lock", text="")

    def draw(self, context):
        cam = context.scene.camera.data
        settings = cam.focal_lock
        layout = self.layout
        layout.enabled = settings.enable_lock

        col = layout.column()

        # Property to set the focus object
        col.prop(settings, "focus_object", text="Focus Object")

        # Mechanics
        col = layout.column()
        # col.prop(settings, 'enable_lock')
        col.prop(settings, 'enable_track')
        col = layout.column()
        sub = col.column(align=True)
        sub.prop(cam, 'lens', text="Focal Length")


class FOCALLOCK_PT_BakeSettings(Panel):
    # COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}
    bl_category = "Focal Lock"
    bl_label = "Focal Lock Baking"
    bl_parent_id = "FOCALLOCK_PT_FocalLock"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.camera and context.active_object == context.scene.camera

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.bake_focal_length")
        layout.operator("wm.clear_bake_focal_length")
        layout.label(text="Bake focal length keyframes for active camera")


# PROPERTIES

class FocalLockSettings(PropertyGroup):
    # These "original" properties aren't ever exposed to the UI.
    # It's not a huge thing, but there is another way to store this without the overhead
    # of making a FloatProperty.
    original_distance = FloatProperty(
        name="Original Distance",
        description="This is the distance that the camera originally was from the focus object",
        )
    original_focal_length = FloatProperty(
        name="Original Focal Length",
        description="The focal length when the user clicked enabled",
        )
    focal_distance_ratio = FloatProperty(
        name="Focal Distance Ratio",
        description="Ratio of the original focal length over the original distance",
        )
    focus_object = PointerProperty(
        name="Focus Object",
        type=Object,
        description="The object you would like the camera to focus on",
        update=update_focus_object
        )
    enable_lock = BoolProperty(
        name="Lock",
        description="Lock camera zoom to focus object",
        default=False,
        update=update_enable_lock
        )
    enable_track = BoolProperty(
        name="Track camera to object",
        description="Add a tracking constraint to camera so it always stays focussed on the object",
        default=False,
        update=update_enable_track
        )


# REGISTRATION AND UNREGISTRATION

classes = (
    FOCALLOCK_PT_FocalLock,
    FocalLockSettings,
    BakeFocalLength,
    ClearBakeFocalLength,
    FOCALLOCK_PT_BakeSettings
    )

handlers = [bpy.app.handlers.scene_update_post, bpy.app.handlers.frame_change_post, bpy.app.handlers.load_post]


def register():
    for cls in classes:
        register_class(cls)

    Camera.focal_lock = PointerProperty(type=FocalLockSettings)

    for handler in handlers:
        [handler.remove(h) for h in handler if h.__name__ == "update_focal_length"]
        handler.append(update_focal_length)


def unregister():
    for cls in classes:
        unregister_class(cls)

    del Camera.focal_lock

    for handler in handlers:
        [handler.remove(h) for h in handler if h.__name__ == "update_focal_length"]


if __name__ == "__main__":
    register()
